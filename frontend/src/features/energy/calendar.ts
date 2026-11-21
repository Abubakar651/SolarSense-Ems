import type { DailyEnergyDay } from '@/types/domain/energy';

/** One day in the month grid; solarKwh is null for a day with no figures. */
export interface CalendarDay {
  date: string;
  day: number;
  solarKwh: number | null;
}

/** "2026-08" for every month the rows cover, oldest first. */
export function monthsCovered(days: readonly DailyEnergyDay[]): string[] {
  return [...new Set(days.map(({ date }) => date.slice(0, 7)))].sort();
}

/**
 * The month as calendar weeks starting on Monday, padded with nulls before the 1st and after the
 * last day so every week has seven slots.
 */
export function monthWeeks(
  month: string,
  days: readonly DailyEnergyDay[],
): (CalendarDay | null)[][] {
  const [year, monthIndex] = [Number(month.slice(0, 4)), Number(month.slice(5, 7)) - 1];
  const daysInMonth = new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
  const mondayOffset = (new Date(Date.UTC(year, monthIndex, 1)).getUTCDay() + 6) % 7;
  const solarByDate = new Map(days.map(({ date, solarKwh }) => [date, solarKwh]));

  const slots: (CalendarDay | null)[] = Array<null>(mondayOffset).fill(null);
  for (let day = 1; day <= daysInMonth; day++) {
    const date = `${month}-${String(day).padStart(2, '0')}`;
    slots.push({ date, day, solarKwh: solarByDate.get(date) ?? null });
  }
  while (slots.length % 7 !== 0) slots.push(null);

  const weeks: (CalendarDay | null)[][] = [];
  for (let i = 0; i < slots.length; i += 7) weeks.push(slots.slice(i, i + 7));
  return weeks;
}

/** Where a value sits between the month's lowest and highest day, from 0 to 1 (1 when all days are equal). */
export function intensity(value: number, min: number, max: number): number {
  return max > min ? (value - min) / (max - min) : 1;
}
