import { niceMax } from '@/lib/charts/nice-max';
import type { CurvePoint } from '@/types/domain/energy';

/** Line colours of the power curve, shared by the chart and its legend (the chart is a client module). */
export const CURVE_COLORS = {
  pv: 'var(--accent)',
  load: 'var(--primary)',
  battery: 'var(--ok)',
  grid: 'var(--muted)',
} as const;

/**
 * The kW axis for a curve. Battery and grid go negative (discharging, importing), so the axis is symmetric
 * around zero when any point is negative and starts at zero otherwise.
 */
export function kwRange(points: readonly CurvePoint[]): { min: number; max: number } {
  const values = points
    .flatMap((p) => [p.pvKw, p.loadKw, p.batteryKw, p.gridKw])
    .filter((v) => v !== null);
  const peak = Math.max(1, ...values.map((v) => Math.abs(v)));
  // Negative values mirror the axis, so each half gets two steps; otherwise the axis starts at zero with four.
  if (values.some((v) => v < 0)) {
    const { max } = niceMax(peak * 1.05, 2);
    return { min: -max, max };
  }
  return { min: 0, max: niceMax(peak * 1.05).max };
}

/** The days either side of `date` in the site's available days; null at the ends. */
export function neighbourDays(
  dates: readonly string[],
  date: string,
): { previous: string | null; next: string | null } {
  const i = dates.indexOf(date);
  if (i === -1) return { previous: null, next: null };
  return { previous: dates[i - 1] ?? null, next: dates[i + 1] ?? null };
}

/** "06:30" -> 6.5 hours into the day. */
export const hoursOf = (time: string) => Number(time.slice(0, 2)) + Number(time.slice(3, 5)) / 60;

/** Draws a gap wherever the value is null. */
export function linePath(
  points: readonly CurvePoint[],
  pick: (p: CurvePoint) => number | null,
  x: (p: CurvePoint) => number,
  y: (v: number) => number,
): string {
  let d = '';
  let drawing = false;
  for (const p of points) {
    const v = pick(p);
    if (v === null) {
      drawing = false;
      continue;
    }
    d += `${drawing ? 'L' : 'M'}${x(p).toFixed(1)},${y(v).toFixed(1)}`;
    drawing = true;
  }
  return d;
}
