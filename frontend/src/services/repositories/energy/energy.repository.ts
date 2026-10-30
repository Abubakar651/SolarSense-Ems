import type { DayPlan } from '@/types/domain/energy';

export interface EnergyRepository {
  /** Today's hourly plan: solar, usage, battery level and grid import. */
  getDayPlan(): Promise<DayPlan>;
}
