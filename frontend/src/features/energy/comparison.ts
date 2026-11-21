import type { MonthEnergy } from '@/types/domain/energy';
import { monthName } from './monitoring';

export interface YearComparison {
  labels: string[];
  currentYear: string;
  previousYear: string;
  /** Solar generated per calendar month, Jan to Dec; null for a month with no figures. */
  current: (number | null)[];
  previous: (number | null)[];
}

/**
 * Solar generated per month in the latest year against the year before. Null while no month has
 * figures in both years, because there is nothing to compare yet.
 */
export function yearComparison(months: readonly MonthEnergy[]): YearComparison | null {
  const latest = months[months.length - 1];
  if (!latest) return null;
  const currentYear = latest.month.slice(0, 4);
  const previousYear = String(Number(currentYear) - 1);
  const byMonth = new Map(months.map((m) => [m.month, m.solarKwh]));
  const slots = Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0'));
  const current = slots.map((slot) => byMonth.get(`${currentYear}-${slot}`) ?? null);
  const previous = slots.map((slot) => byMonth.get(`${previousYear}-${slot}`) ?? null);
  if (!current.some((value, i) => value !== null && previous[i] !== null)) return null;
  return {
    labels: slots.map((slot) => monthName(`${currentYear}-${slot}`)),
    currentYear,
    previousYear,
    current,
    previous,
  };
}
