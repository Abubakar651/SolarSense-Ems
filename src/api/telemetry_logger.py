"""
Background logger that records every connected site's inverter every few minutes (inverter_samples).

Each site with an inverter address is polled through its own reader, and its samples are stored under
its site id only. The logger has to outlive any single failure: an unreachable inverter or a database
hiccup is logged once when it starts and once when it clears (per site), and polling carries on.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
import logging
import threading
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from src.api.db.models import InverterSample, Site
from src.data_engineering.goodwe_live_reader import GoodWeLiveReader, GoodWeLiveTelemetryDTO
from src.forecast.live_forecast import TelemetrySample

log = logging.getLogger(__name__)

# Sites are polled concurrently, but their writes go one at a time: SQLite (tests, local runs) shares a
# single connection, and concurrent use of it fails ("bad parameter or other API misuse"). A handful of
# one-row inserts every few minutes costs nothing serialised.
_store_lock = threading.Lock()


class ReaderPool:
    """One reader (and so one inverter connection and lock) per inverter address."""

    def __init__(self, make_reader: Callable[[str], GoodWeLiveReader] = lambda host: GoodWeLiveReader(host=host)) -> None:
        self._make = make_reader
        self._readers: dict[str, GoodWeLiveReader] = {}

    def get(self, host: str) -> GoodWeLiveReader:
        reader = self._readers.get(host)
        if reader is None:
            reader = self._readers[host] = self._make(host)
        return reader


def sample_from_telemetry(site_id: uuid.UUID, telemetry: GoodWeLiveTelemetryDTO) -> InverterSample:
    return InverterSample(
        site_id=site_id,
        recorded_at=datetime.fromisoformat(telemetry.timestamp_iso),
        pv_power_w=max(0.0, telemetry.total_pv_power_w),
        load_power_w=max(0.0, telemetry.house_consumption_w),
        grid_power_w=telemetry.grid_active_power_w,
        battery_power_w=telemetry.battery_power_w,
        battery_soc_pct=telemetry.battery_soc_pct,
        is_blackout=telemetry.is_blackout,
    )


def store_sample(session_factory: sessionmaker[Session], sample: InverterSample) -> None:
    """Stores one sample; a reading with the same site and timestamp as a stored one is skipped."""
    values = {c.key: getattr(sample, c.key) for c in InverterSample.__table__.columns}
    with _store_lock, session_factory() as session:
        insert = pg_insert if session.get_bind().dialect.name == "postgresql" else sqlite_insert
        session.execute(insert(InverterSample).values(values).on_conflict_do_nothing())
        session.commit()


def serial_matches(telemetry: GoodWeLiveTelemetryDTO, site_serial: str) -> bool:
    """
    Whether a reading came from the site's own inverter. Private addresses repeat across homes and any
    user can save any address, so the address alone doesn't prove whose inverter answered.
    """
    return telemetry.serial_number.strip().upper() == site_serial.strip().upper()


def connected_sites(session_factory: sessionmaker[Session]) -> list[tuple[uuid.UUID, str, str]]:
    """(site id, inverter address, inverter serial) for every site with an address."""
    with session_factory() as session:
        rows = session.execute(
            select(Site.id, Site.inverter_host, Site.inverter_serial).where(Site.inverter_host.is_not(None))
        ).all()
    return [(site_id, host, serial) for site_id, host, serial in rows]


def load_samples(
    session_factory: sessionmaker[Session], site_id: uuid.UUID, start: datetime, end: datetime
) -> list[TelemetrySample]:
    """One site's samples with start <= recorded_at <= end, oldest first."""
    with session_factory() as session:
        rows = session.scalars(
            select(InverterSample)
            .where(
                InverterSample.site_id == site_id,
                InverterSample.recorded_at >= start,
                InverterSample.recorded_at <= end,
            )
            .order_by(InverterSample.recorded_at)
        ).all()
    return [
        TelemetrySample(
            recorded_at=r.recorded_at,
            pv_power_w=r.pv_power_w,
            load_power_w=r.load_power_w,
            battery_soc_pct=r.battery_soc_pct,
            is_blackout=r.is_blackout,
            grid_power_w=r.grid_power_w,
            battery_power_w=r.battery_power_w,
        )
        for r in rows
    ]


async def poll_site(
    readers: ReaderPool, session_factory: sessionmaker[Session], site_id: uuid.UUID, host: str, serial: str
) -> None:
    """
    Reads one site's inverter and stores the sample. Raises whatever the read or the write raised, and
    ValueError (storing nothing) when the inverter at the address isn't the site's own.
    """
    telemetry = await readers.get(host).fetch_telemetry()
    if not serial_matches(telemetry, serial):
        raise ValueError("inverter_serial_mismatch")
    sample = sample_from_telemetry(site_id, telemetry)
    await asyncio.to_thread(store_sample, session_factory, sample)


async def run_inverter_logger(
    readers: ReaderPool,
    session_factory: sessionmaker[Session],
    interval_seconds: float,
) -> None:
    """Polls every connected site until cancelled (the API lifespan cancels it on shutdown)."""
    failing: set[uuid.UUID] = set()
    while True:
        try:
            sites = await asyncio.to_thread(connected_sites, session_factory)
        except Exception:
            log.warning("Could not list sites to poll; retrying in %.0f s", interval_seconds, exc_info=True)
            sites = []
        results = await asyncio.gather(
            *(poll_site(readers, session_factory, site_id, host, serial) for site_id, host, serial in sites),
            return_exceptions=True,
        )
        for (site_id, _host, _serial), result in zip(sites, results):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                if site_id not in failing:
                    log.warning("Telemetry logging failed for site %s", site_id, exc_info=result)
                failing.add(site_id)
            elif site_id in failing:
                log.info("Telemetry logging recovered for site %s", site_id)
                failing.discard(site_id)
        await asyncio.sleep(interval_seconds)
