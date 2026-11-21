import { backupHours, backupHoursAt } from '@/lib/backup-hours';
import { todayInKarachi } from '@/lib/freshness';
import { pad } from '@/lib/format';
import type { ClockTime, DayPlan } from '@/types/domain/energy';
import type { InverterReading } from '@/types/domain/inverter';

/**
 * Where the "right now" figures come from: the plan's current hour (sample data), the inverter,
 * or the plan's current hour because the inverter can't be reached.
 */
export type NowSource = 'plan' | 'live' | 'offline';

/** Everything the dashboard shows for one moment of the day. */
export interface DashboardSnapshot {
  source: NowSource;
  grid: { label: string; tone: 'ok' | 'bad' | 'neutral' };
  solarKw: number;
  loadKw: number;
  chargeKw: number;
  gridKw: number;
  /** Solar left over after the home and the battery are served. */
  exportKw: number;
  soc: number;
  batterySub: string;
  backupHours: string;
  /** "2h 18m" until the peak window, "Now" while it lasts, "Ended" after it. */
  peakCountdown: string;
  peakNote: string;
  flowSummary: string;
}

interface PowerNow {
  solarKw: number;
  loadKw: number;
  chargeKw: number;
  dischargeKw: number;
  gridKw: number;
  exportKw: number;
  soc: number;
}

function plannedNow(plan: DayPlan, hour: number): PowerNow {
  const solarKw = plan.solar[hour] as number;
  const loadKw = plan.load[hour] as number;
  const chargeKw = plan.charge[hour] as number;
  return {
    solarKw,
    loadKw,
    chargeKw,
    dischargeKw: 0,
    gridKw: plan.grid[hour] as number,
    exportKw: Math.max(0, solarKw - loadKw - chargeKw),
    soc: plan.soc[hour] as number,
  };
}

/** Inverter sign conventions: battery power + is charging, grid power + is exporting. */
function measuredNow(reading: Extract<InverterReading, { status: 'online' }>): PowerNow {
  const { data } = reading;
  return {
    solarKw: data.totalPvPowerW / 1000,
    loadKw: data.houseConsumptionW / 1000,
    chargeKw: Math.max(0, data.batteryPowerW) / 1000,
    dischargeKw: Math.max(0, -data.batteryPowerW) / 1000,
    gridKw: Math.max(0, -data.gridActivePowerW) / 1000,
    exportKw: Math.max(0, data.gridActivePowerW) / 1000,
    soc: Math.round(data.batterySocPct),
  };
}

function flowSummaryOf(p: PowerNow): string {
  return (
    `Solar ${p.solarKw.toFixed(1)} kW is powering your home (${p.loadKw.toFixed(1)} kW)` +
    (p.chargeKw > 0 ? ` and charging the battery (${p.chargeKw.toFixed(1)} kW)` : '') +
    (p.dischargeKw > 0 ? `, with the battery supplying ${p.dischargeKw.toFixed(1)} kW` : '') +
    (p.exportKw > 0 ? `, with ${p.exportKw.toFixed(1)} kW exported to the grid` : '') +
    (p.gridKw > 0
      ? `, with ${p.gridKw.toFixed(1)} kW coming from the grid`
      : '. No grid power is being used') +
    '.'
  );
}

function batterySubOf(p: PowerNow, source: NowSource): string {
  if (p.chargeKw > 0) {
    return source === 'live'
      ? `Charging at ${p.chargeKw.toFixed(1)} kW`
      : `Charging at ${p.chargeKw.toFixed(1)} kW from solar`;
  }
  if (p.dischargeKw > 0) return `Powering your home at ${p.dischargeKw.toFixed(1)} kW`;
  return p.soc >= 100 ? 'Full. Ready for peak hours' : 'Idle';
}

function gridBadge(reading: InverterReading | null): DashboardSnapshot['grid'] {
  if (reading === null) return { label: 'Grid connected', tone: 'ok' };
  if (reading.status === 'offline') return { label: 'Inverter offline', tone: 'neutral' };
  return reading.data.isBlackout
    ? { label: 'Grid down', tone: 'bad' }
    : { label: 'Grid connected', tone: 'ok' };
}

/**
 * The dashboard at one moment. With an online inverter reading, the "now" figures are measured;
 * without one (sample data) or with the inverter offline, they are the plan's for the current hour.
 */
export function dashboardSnapshot(
  plan: DayPlan,
  now: ClockTime,
  reading: InverterReading | null = null,
): DashboardSnapshot {
  const { hour, minute } = now;
  const source: NowSource =
    reading === null ? 'plan' : reading.status === 'online' ? 'live' : 'offline';
  const power = reading?.status === 'online' ? measuredNow(reading) : plannedNow(plan, hour);
  const { solarKw, loadKw, chargeKw, gridKw, exportKw, soc } = power;

  const minutesToPeak = plan.peakStartHour * 60 - (hour * 60 + minute);
  const peakOver = hour >= plan.peakEndHour;
  const peakCountdown =
    minutesToPeak > 0
      ? `${Math.floor(minutesToPeak / 60)}h ${minutesToPeak % 60}m`
      : peakOver
        ? 'Ended'
        : 'Now';
  // plan.soc[h] is the level at the end of hour h, so the level as the peak starts ends the hour before.
  const socAtPeak = plan.soc[plan.peakStartHour - 1] ?? soc;

  return {
    source,
    grid: gridBadge(reading),
    solarKw,
    loadKw,
    chargeKw,
    gridKw,
    exportKw,
    soc,
    batterySub: batterySubOf(power, source),
    // A load the inverter didn't report (0 W) can't size the backup; use the plan's usage for the hour.
    backupHours:
      source === 'live'
        ? backupHoursAt(plan, soc, loadKw > 0 ? loadKw : (plan.load[hour] as number))
        : backupHours(plan, hour),
    peakCountdown,
    peakNote: peakNoteOf(plan, soc, socAtPeak, minutesToPeak, peakOver),
    flowSummary: flowSummaryOf(power),
  };
}

function peakNoteOf(
  plan: DayPlan,
  soc: number,
  socAtPeak: number,
  minutesToPeak: number,
  peakOver: boolean,
): string {
  if (peakOver) return `Today's peak hours have ended. Battery at ${soc}%.`;
  if (minutesToPeak <= 0) return `Peak hours have started. Battery at ${soc}%.`;
  if (soc >= 100) return 'Battery is full and ready for the evening peak.';
  return `Battery should reach about ${socAtPeak}% by ${pad(plan.peakStartHour)}:00.`;
}

/** Figures for the whole sample day that do not move with the clock. */
export interface DayFacts {
  /** What the plan saves over the day compared with no solar or battery (PKR). */
  savedTodayPkr: number;
  /** Highest hourly solar output and the hour it falls in. */
  peakSolar: { kw: number; hour: number };
  peakStart: string;
}

const inPeak = (plan: DayPlan, hour: number) =>
  hour >= plan.peakStartHour && hour < plan.peakEndHour;

/**
 * Savings are the grid energy the plan avoids (usage minus grid import, at that hour's rate)
 * plus the solar left over after the home and battery, credited at the export rate.
 */
export function dayFacts(plan: DayPlan): DayFacts {
  const { peakPkr, offPeakPkr, exportPkr } = plan.tariff;
  let savedTodayPkr = 0;
  for (let hour = 0; hour < plan.solar.length; hour++) {
    const rate = inPeak(plan, hour) ? peakPkr : offPeakPkr;
    const load = plan.load[hour] as number;
    const exportKw = Math.max(
      0,
      (plan.solar[hour] as number) - load - (plan.charge[hour] as number),
    );
    savedTodayPkr += (load - (plan.grid[hour] as number)) * rate + exportKw * exportPkr;
  }

  const peakKw = Math.max(...plan.solar);
  return {
    savedTodayPkr,
    peakSolar: { kw: peakKw, hour: plan.solar.indexOf(peakKw) },
    peakStart: `${pad(plan.peakStartHour)}:00`,
  };
}

/** A same-shaped plan of all zeros, for Dashboard/Plan while the site has no plan yet. */
export function zeroDayPlan(): DayPlan {
  const zeroHours = () => Array.from({ length: 24 }, () => 0);
  return {
    isSample: false,
    sampleDate: todayInKarachi(new Date()),
    tariff: { peakPkr: 0, offPeakPkr: 0, exportPkr: 0 },
    solar: zeroHours(),
    load: zeroHours(),
    soc: zeroHours(),
    grid: zeroHours(),
    charge: zeroHours(),
    peakStartHour: 18,
    peakEndHour: 22,
    batteryCapacityKwh: 1,
    reserveFloorKwh: 1,
    clockStart: { hour: 0, minute: 0 },
    forecast: null,
    initialSocAssumed: false,
  };
}

/**
 * Says how much of the forecast's recent history came from the inverter log, while it is less than
 * all of it. Null for sample data and once the log covers the whole history.
 */
export function forecastNote(plan: DayPlan): string | null {
  const assumed = plan.initialSocAssumed
    ? 'Starting battery level assumed (no reading near midnight).'
    : null;
  if (plan.forecast === null) return assumed;
  const { loggedHistoryHours, historyHours } = plan.forecast;
  if (loggedHistoryHours >= historyHours) return assumed;
  const days = (hours: number) => Math.floor(hours / 24);
  const history =
    `Forecast from today's weather. Only ${days(loggedHistoryHours)} of the ${days(historyHours)} days of ` +
    'recent history it needs are logged from your inverter yet, so the gaps are filled in from the hours that are and it is less accurate.';
  return assumed === null ? history : `${history} ${assumed}`;
}
