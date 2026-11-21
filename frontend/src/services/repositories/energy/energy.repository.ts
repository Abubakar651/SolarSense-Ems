import type { DayCurve, DayPlanResult, EnergyHistory } from '@/types/domain/energy';
import type { HistoryResult } from '@/types/domain/history';

export interface EnergyRepository {
  /** Today's hourly plan (solar, usage, battery level and grid import), or why there is none yet. */
  getDayPlan(): Promise<DayPlanResult>;
  /** Day-by-day and month-by-month solar, usage, import and export, oldest first. */
  getEnergyHistory(): Promise<HistoryResult<EnergyHistory>>;
  /**
   * One day's power curve (the site's latest day when `date` is omitted or it has none for it);
   * null while the site has no data at all.
   */
  getDayCurve(date?: string): Promise<DayCurve | null>;
}
