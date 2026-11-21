/**
 * Today's brief from POST /api/agent/advisory/today (DailyBriefResponse in src/api/schemas.py),
 * in camelCase. Text is written by the backend; the UI only lays it out.
 */
export interface AdvisoryMetrics {
  solarGenerationKwh: number;
  householdLoadKwh: number;
  gridImportKwh: number;
  /** Null when the plan does not model exports (the backend always sends a number). */
  netMeteringExportKwh: number | null;
  exportRevenuePkr: number | null;
  peakBatteryDischargeKwh: number;
  outageHours: number;
  /** Optimiser result against no-battery baseline; null when no optimiser ran. */
  netSavingsPkr: number | null;
  /** Null while the site's dust estimate is still collecting days, or can't be worked out today. */
  soilingLossKwh: number | null;
  netCleaningBenefitPkr: number | null;
}

export interface Advisory {
  /** YYYY-MM-DD */
  date: string;
  headline: string;
  dispatchArbitrageBrief: string;
  blackoutResilienceBrief: string;
  soilingMaintenanceBrief: string;
  recommendedActions: string[];
  keyMetrics: AdvisoryMetrics;
  /** How the text was produced, e.g. "deterministic_template". */
  generationMode: string;
  /** True while the text is built from the recorded sample day. */
  isSample: boolean;
}

/** The brief, or "unavailable" when today's plan it is written from can't be made (no weather forecast). */
export type AdvisoryResult = { status: 'ready'; advisory: Advisory } | { status: 'unavailable' };
