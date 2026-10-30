import type { DayPlan } from '@/types/domain/energy';

const DISCHARGE_EFFICIENCY = 0.95;

/** Hours the battery could carry the home at the given hour's usage, keeping the outage reserve untouched. */
export function backupHours(plan: DayPlan, hour: number): string {
  const loadKw = plan.load[hour] as number;
  const soc = plan.soc[hour] as number;
  const usableKwh = (soc / 100) * plan.batteryCapacityKwh - plan.reserveFloorKwh;

  return Math.max(0, (usableKwh * DISCHARGE_EFFICIENCY) / loadKw).toFixed(1);
}
