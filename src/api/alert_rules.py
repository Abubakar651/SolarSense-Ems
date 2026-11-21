"""
Turns a site's data into alerts for its user.

Pure functions: given the data, they return the alerts that should exist. Each alert's id is derived from
(user, alert type, event), so creating the same alert twice is a no-op and its read state survives.

Generated types, each only while the user has it switched on for in-app notifications:
- grid_outage:  outages in the site's telemetry log, and (station site only) "Grid Power Outage" events in the
                recorded alarm log with the protection trips inside them.
- panels_dirty: the backend's own wash rule (SolarPlantLossCalculator) says cleaning pays off, on the site's
                live dust model (src/api/site_soiling.py); the station's recorded model until it has one.
- peak_soon:    today's seasonal peak window, from 30 minutes before it starts.
- inverter_offline: a connected inverter (site.inverter_host) sent no sample for 30 minutes.
Not generated (no trustworthy source yet): outage_risk, weekly_digest.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import uuid
from zoneinfo import ZoneInfo

from src.api.insights import OutageEventOut

SITE_TZ = ZoneInfo("Asia/Karachi")
# Fixed namespace so ids are stable across restarts and servers.
ALERT_NAMESPACE = uuid.UUID("5b0e7c1a-2f5d-4c1e-9a7e-3d2b8f6c4a10")
CRITICAL_OUTAGE_MINUTES = 15
PEAK_NOTICE = timedelta(minutes=30)
# A connected inverter polled every 5 minutes that has sent nothing for this long is treated as offline.
INVERTER_SILENCE = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class AlertCandidate:
    id: uuid.UUID
    kind: str
    severity: str
    title: str
    detail: str
    created_at: datetime


def alert_id(user_id: uuid.UUID, kind: str, event_key: str) -> uuid.UUID:
    return uuid.uuid5(ALERT_NAMESPACE, f"{user_id}:{kind}:{event_key}")


def _local(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=SITE_TZ)


def _duration_label(minutes: int) -> str:
    hours, rest = divmod(minutes, 60)
    return f"{rest} m" if hours == 0 else f"{hours} h {rest:02d} m"


def grid_outage_alerts(user_id: uuid.UUID, alarms: list[dict[str, object]]) -> list[AlertCandidate]:
    """One alert per grid-loss alarm; the inverter's protection trips inside that window are listed with it."""
    rows = [
        {**a, "start": _local(str(a["start_time"])), "end": _local(str(a["end_time"]))}
        for a in alarms
        if a.get("start_time") and a.get("end_time")
    ]
    out: list[AlertCandidate] = []
    for outage in (r for r in rows if "Grid Power Outage" in str(r["alarm_name"])):
        related = [
            str(r["alarm_name"])
            for r in rows
            if r is not outage and r["start"] >= outage["start"] and r["end"] <= outage["end"]
        ]
        minutes = round(float(str(outage["duration_minutes"])))
        out.append(
            AlertCandidate(
                id=alert_id(user_id, "grid_outage", str(outage["start_time"])),
                kind="grid_outage",
                severity="crit" if minutes >= CRITICAL_OUTAGE_MINUTES else "warn",
                title=f"Grid outage {str(outage['status']).lower()}",
                detail=(
                    f"Grid power was lost for {_duration_label(minutes)}. "
                    f"Inverter faults: {', '.join([str(outage['alarm_name']), *related])}."
                ),
                created_at=outage["start"],
            )
        )
    return out


def panels_dirty_alert(
    user_id: uuid.UUID, as_of: str, daily_kwh_lost: float, decision: dict[str, object], event_key: str | None = None
) -> list[AlertCandidate]:
    """
    Only when the wash rule decided cleaning pays off before the next rain. `event_key` (default as_of)
    names the dust build-up the alert is about, so one build-up raises one alert.
    """
    if not str(decision.get("decision", "")).startswith("TRIGGER"):
        return []
    return [
        AlertCandidate(
            id=alert_id(user_id, "panels_dirty", event_key or as_of),
            kind="panels_dirty",
            severity="warn",
            title="Panels need cleaning",
            detail=(
                f"Dust is costing about {daily_kwh_lost:.1f} kWh a day. Washing now is worth more "
                f"(PKR {float(str(decision['projected_loss_before_rain_pkr'])):,.0f} before the next rain) "
                f"than it costs (PKR {float(str(decision['wash_cost_pkr'])):,.0f})."
            ),
            created_at=datetime.combine(date.fromisoformat(as_of), time(9, 0), SITE_TZ),
        )
    ]


def logged_outage_alerts(user_id: uuid.UUID, events: list[OutageEventOut]) -> list[AlertCandidate]:
    """One alert per outage found in the site's own telemetry log (src/api/telemetry_history.py)."""
    out: list[AlertCandidate] = []
    for e in events:
        started = datetime.combine(date.fromisoformat(e.date), time.fromisoformat(e.start), SITE_TZ)
        minutes = round(e.minutes)
        out.append(
            AlertCandidate(
                id=alert_id(user_id, "grid_outage", f"log:{started.isoformat()}"),
                kind="grid_outage",
                severity="crit" if minutes >= CRITICAL_OUTAGE_MINUTES else "warn",
                title="Grid outage",
                detail=(
                    f"Grid power was lost for {_duration_label(minutes)} from {e.start} to {e.end}. "
                    f"The battery carried about {e.energy_kwh:.1f} kWh of your home's use."
                ),
                created_at=started,
            )
        )
    return out


def inverter_offline_alert(
    user_id: uuid.UUID, last_sample_at: datetime | None, connected_at_least_since: datetime, now: datetime
) -> list[AlertCandidate]:
    """
    When a connected inverter has sent nothing for INVERTER_SILENCE. One alert per silence: it is keyed
    by the last sample seen, so a new silence after the inverter came back raises a new alert.
    """
    quiet_since = last_sample_at or connected_at_least_since
    if now - quiet_since < INVERTER_SILENCE:
        return []
    key = last_sample_at.isoformat() if last_sample_at else "never"
    return [
        AlertCandidate(
            id=alert_id(user_id, "inverter_offline", key),
            kind="inverter_offline",
            severity="warn",
            title="Inverter not responding",
            detail=(
                "SolarSense hasn't received a reading from your inverter since "
                f"{quiet_since.astimezone(SITE_TZ):%b %d, %H:%M}. Check that it is on and connected to your network."
                if last_sample_at
                else "SolarSense hasn't received any reading from your inverter yet. "
                "Check the address in Settings and that the inverter is on your network."
            ),
            created_at=quiet_since + INVERTER_SILENCE,
        )
    ]


def peak_soon_alert(
    user_id: uuid.UUID, day: str, peak_start_hour: int, peak_end_hour: int, now: datetime | None = None
) -> list[AlertCandidate]:
    """Shown from PEAK_NOTICE before the peak starts; `now` None skips that check (a recorded day)."""
    starts = datetime.combine(date.fromisoformat(day), time(peak_start_hour, 0), SITE_TZ)
    if now is not None and now < starts - PEAK_NOTICE:
        return []
    return [
        AlertCandidate(
            id=alert_id(user_id, "peak_soon", day),
            kind="peak_soon",
            severity="info",
            title=f"Peak hours start at {peak_start_hour:02d}:00",
            detail=(
                f"Grid power costs more from {peak_start_hour:02d}:00 to {peak_end_hour:02d}:00. "
                "The plan keeps the battery for these hours."
            ),
            created_at=starts - PEAK_NOTICE,
        )
    ]
