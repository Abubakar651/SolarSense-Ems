import { todayInKarachi } from '@/lib/freshness';
import type { DailyEnergyDay, EnergyHistory, MonthEnergy } from '@/types/domain/energy';

export type EnergyRange = 'week' | 'month' | 'year';

const MONTH_NAMES = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const DAY_MS = 86_400_000;
const DAYS: Record<'week' | 'month', number> = { week: 7, month: 30 };
const YEAR_MONTHS = 12;

export const monthName = (month: string) => MONTH_NAMES[Number(month.slice(5, 7)) - 1] as string;

export interface RangeSeries {
  labels: string[];
  generation: number[];
  consumption: number[];
  imported: number[];
  exported: number[];
}

export interface RangeTotals {
  generationKwh: number;
  consumptionKwh: number;
  importKwh: number;
  exportKwh: number;
  /** Solar the site used itself: generated minus exported. */
  selfConsumedKwh: number;
  /** Null when no day in the range measured the battery. */
  batteryChargedKwh: number | null;
  batteryDischargedKwh: number | null;
}

const sum = (values: readonly number[]) => values.reduce((a, b) => a + b, 0);

/** Sum of the measured values, or null when none were. */
function sumMeasured(values: readonly (number | null | undefined)[]): number | null {
  const measured = values.filter((v): v is number => v != null);
  return measured.length ? sum(measured) : null;
}

/**
 * The last `days` calendar days through the latest row: logged days can have gaps, so the last N rows
 * could span far more than N days.
 */
function lastDays(days: readonly DailyEnergyDay[], count: number): DailyEnergyDay[] {
  const latest = days[days.length - 1]?.date;
  if (!latest) return [];
  const cutoff = new Date(Date.parse(`${latest}T00:00:00Z`) - count * DAY_MS)
    .toISOString()
    .slice(0, 10);
  return days.filter(({ date }) => date > cutoff);
}

const dayLabel = (range: 'week' | 'month', date: string) =>
  range === 'week'
    ? (WEEKDAYS[new Date(`${date}T00:00:00Z`).getUTCDay()] as string)
    : String(Number(date.slice(8)));

/** A same-shaped history of all zeros, for the Energy screen while the site has none yet. */
export function zeroEnergyHistory(): EnergyHistory {
  const today = new Date(`${todayInKarachi(new Date())}T00:00:00Z`);
  const days: DailyEnergyDay[] = Array.from({ length: 30 }, (_, i) => {
    const date = new Date(today.getTime() - (29 - i) * DAY_MS).toISOString().slice(0, 10);
    return { date, solarKwh: 0, loadKwh: 0, importKwh: 0, exportKwh: 0 };
  });
  const months: MonthEnergy[] = Array.from({ length: 24 }, (_, i) => {
    const monthDate = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() - (23 - i), 1));
    const month = `${monthDate.getUTCFullYear()}-${String(monthDate.getUTCMonth() + 1).padStart(2, '0')}`;
    return { month, solarKwh: 0, loadKwh: 0, importKwh: 0, exportKwh: 0 };
  });
  return { days, months };
}

/** The energy flows for the chosen range: daily bars for 7 or 30 days, monthly bars for the last 12 months. */
export function energyRange(
  history: EnergyHistory,
  range: EnergyRange,
): { series: RangeSeries; totals: RangeTotals } {
  const rows =
    range === 'year'
      ? history.months.slice(-YEAR_MONTHS).map((m) => ({
          label: monthName(m.month),
          solar: m.solarKwh,
          load: m.loadKwh,
          imported: m.importKwh,
          exported: m.exportKwh,
          charged: null,
          discharged: null,
        }))
      : lastDays(history.days, DAYS[range]).map((d) => ({
          label: dayLabel(range, d.date),
          solar: d.solarKwh,
          load: d.loadKwh,
          imported: d.importKwh,
          exported: d.exportKwh,
          charged: d.batteryChargedKwh,
          discharged: d.batteryDischargedKwh,
        }));

  const generationKwh = sum(rows.map((r) => r.solar));
  const exportKwh = sum(rows.map((r) => r.exported));
  return {
    series: {
      labels: rows.map((r) => r.label),
      generation: rows.map((r) => r.solar),
      consumption: rows.map((r) => r.load),
      imported: rows.map((r) => r.imported),
      exported: rows.map((r) => r.exported),
    },
    totals: {
      generationKwh,
      consumptionKwh: sum(rows.map((r) => r.load)),
      importKwh: sum(rows.map((r) => r.imported)),
      exportKwh,
      selfConsumedKwh: Math.max(0, generationKwh - exportKwh),
      batteryChargedKwh: sumMeasured(rows.map((r) => r.charged)),
      batteryDischargedKwh: sumMeasured(rows.map((r) => r.discharged)),
    },
  };
}
