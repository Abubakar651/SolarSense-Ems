import type { DayPlan } from '@/types/domain/energy';

/** Share of the stored energy that reaches the home when the battery discharges. */
export const DISCHARGE_EFFICIENCY = 0.95;
/** Astronomical night in Lahore (20:00-04:00), when the battery alone carries the home in an outage. */
const NIGHT_HOURS = [20, 21, 22, 23, 0, 1, 2, 3];

/** The home's mean usage (kW) over the night hours of today's plan. */
export function overnightLoadKw(plan: DayPlan): number {
  const night = NIGHT_HOURS.map((hour) => plan.load[hour] as number);
  return night.reduce((sum, kw) => sum + kw, 0) / night.length;
}

/** Hours the battery could carry the home at the given hour's usage, keeping the outage reserve untouched. */
export function backupHours(plan: DayPlan, hour: number): string {
  return backupHoursAt(plan, plan.soc[hour] as number, plan.load[hour] as number);
}

/** The same estimate for a battery level and usage measured right now. */
export function backupHoursAt(plan: DayPlan, socPct: number, loadKw: number): string {
  if (loadKw <= 0) return '0.0';
  const usableKwh = (socPct / 100) * plan.batteryCapacityKwh - plan.reserveFloorKwh;
  return Math.max(0, (usableKwh * DISCHARGE_EFFICIENCY) / loadKw).toFixed(1);
}
