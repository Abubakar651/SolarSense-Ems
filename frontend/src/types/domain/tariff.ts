import type { ProsumerRegime, TariffCategory } from '@/lib/tariff';

/**
 * Money is a string, as the backend sends it (Decimal, ROUND_HALF_EVEN), so no rounding happens in
 * the browser. Field names mirror BillEstimateRequest/Response and ProsumerCompareRequest/Response
 * in src/api/schemas.py, in camelCase.
 */

/** POST /api/v2/bill/estimate */
export interface BillEstimateRequest {
  category: TariffCategory;
  /** Above 0. */
  sanctionedLoadKw: number;
  currentKwh: number;
  peakKwh: number;
  offPeakKwh: number;
  fpaReference2mPriorKwh: number;
  includeElectricityDuty: boolean;
  isAtlFiler: boolean;
}

export interface BillEstimate {
  category: TariffCategory;
  slabId: string;
  currentTotalKwh: string;
  /** Named charges, e.g. peak_energy_charges_pkr, in the order the backend lists them. */
  lineItems: Record<string, string>;
  totalPayablePkr: string;
  totalPayableRoundedRupeePkr: string;
  effectiveAllInRatePkrPerKwh: string;
}

/** POST /api/v2/prosumer/compare */
export interface ProsumerCompareRequest {
  sanctionedLoadKw: number;
  grossPeakImportKwh: number;
  grossOffPeakImportKwh: number;
  grossExportKwh: number;
  fpaReference2mPriorKwh: number;
  includeElectricityDuty: boolean;
  isAtlFiler: boolean;
}

export interface ProsumerSettlement {
  regime: ProsumerRegime;
  netBilledPeakImportKwh: string;
  netBilledOffPeakImportKwh: string;
  netSurplusExportKwh: string;
  exportCreditRatePkrPerKwh: string;
  grossRetailImportBillPkr: string;
  exportCreditPkr: string;
  netPayableAfterCreditsPkr: string;
  closingCreditCarryforwardPkr: string;
}

export interface ProsumerComparison {
  grandfathered: ProsumerSettlement;
  netBilling2026: ProsumerSettlement;
  /** How much less the grandfathered arrangement costs; positive favours grandfathered. */
  grandfatheredAdvantagePkr: string;
}

/** What a bill tool has to show. `null` until the backend is connected (the UI cannot compute these). */
export interface BillToolsDefaults {
  /** Prefill for the forms, from the customer's settings. */
  sanctionedLoadKw: number;
  category: TariffCategory;
  includeElectricityDuty: boolean;
  isAtlFiler: boolean;
}
