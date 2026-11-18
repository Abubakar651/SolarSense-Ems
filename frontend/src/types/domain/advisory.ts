/**
 * The daily brief from POST /api/agent/advisory (AgentAdvisoryResponse in src/api/schemas.py),
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
  soilingLossKwh: number;
  netCleaningBenefitPkr: number;
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
  /** How the text was produced, e.g. "deterministic_physics_synthesizer". */
  generationMode: string;
  /** True while the text is built from the recorded sample day. */
  isSample: boolean;
}
