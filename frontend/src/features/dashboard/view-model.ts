import { backupHours } from '@/lib/backup-hours';
import { pad } from '@/lib/format';
import type { ClockTime, DayPlan } from '@/types/domain/energy';

/** Everything the dashboard shows for one moment of the sample day. */
export interface DashboardSnapshot {
  solarKw: number;
  loadKw: number;
  chargeKw: number;
  gridKw: number;
  /** Solar left over after the home and the battery are served. */
  exportKw: number;
  soc: number;
  batterySub: string;
  backupHours: string;
  /** "2h 18m" until the peak window, or "Now" once it has started. */
  peakCountdown: string;
  peakNote: string;
  flowSummary: string;
}

export function dashboardSnapshot(plan: DayPlan, now: ClockTime): DashboardSnapshot {
  const { hour, minute } = now;
  const solarKw = plan.solar[hour] as number;
  const loadKw = plan.load[hour] as number;
  const chargeKw = plan.charge[hour] as number;
  const gridKw = plan.grid[hour] as number;
  const soc = plan.soc[hour] as number;
  const exportKw = Math.max(0, solarKw - loadKw - chargeKw);

  const minutesToPeak = plan.peakStartHour * 60 - (hour * 60 + minute);
  const peakCountdown =
    minutesToPeak > 0 ? `${Math.floor(minutesToPeak / 60)}h ${minutesToPeak % 60}m` : 'Now';

  const flowSummary =
    `Solar ${solarKw.toFixed(1)} kW is powering your home (${loadKw.toFixed(1)} kW)` +
    (chargeKw > 0 ? ` and charging the battery (${chargeKw.toFixed(1)} kW)` : '') +
    (exportKw > 0 ? `, with ${exportKw.toFixed(1)} kW exported to the grid` : '') +
    (gridKw > 0
      ? `, with ${gridKw.toFixed(1)} kW coming from the grid`
      : '. No grid power is being used') +
    '.';

  return {
    solarKw,
    loadKw,
    chargeKw,
    gridKw,
    exportKw,
    soc,
    batterySub:
      chargeKw > 0
        ? `Charging at ${chargeKw.toFixed(1)} kW from solar`
        : soc >= 100
          ? 'Full. Ready for peak hours'
          : 'Idle',
    backupHours: backupHours(plan, hour),
    peakCountdown,
    peakNote:
      soc >= 100
        ? 'Battery is full and ready for the evening peak.'
        : `Battery should reach about ${soc}%+ by 18:00.`,
    flowSummary,
  };
}

/** Figures for the whole sample day that do not move with the clock. */
export interface DayFacts {
  /** What the plan saves over the day compared with no solar or battery (PKR). */
  savedTodayPkr: number;
  /** Highest hourly solar output and the hour it falls in. */
  peakSolar: { kw: number; hour: number };
  peakStart: string;
  /** "PKR 46.85 vs 34.53 per kWh" */
  rateNote: string;
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
    rateNote: `PKR ${peakPkr} vs ${offPeakPkr} per kWh`,
  };
}
