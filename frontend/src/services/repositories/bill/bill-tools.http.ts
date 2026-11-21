import type { ProsumerRegime, TariffCategory } from '@/lib/tariff';
import type {
  BillEstimate,
  BillEstimateRequest,
  ProsumerCompareRequest,
  ProsumerComparison,
  ProsumerSettlement,
} from '@/types/domain/tariff';
import { apiFetch } from '../../http/client';

/** BillEstimateResponse / ProsumerCompareResponse in src/api/schemas.py. Money is sent as strings. */
interface BillEstimateDto {
  category: string;
  slab_id: string;
  current_total_kwh: string;
  line_items: Record<string, string>;
  total_payable_pkr: string;
  total_payable_rounded_rupee_pkr: string;
  effective_all_in_rate_pkr_per_kwh: string;
}

interface SettlementDto {
  regime: string;
  net_billed_peak_import_kwh: string;
  net_billed_off_peak_import_kwh: string;
  net_surplus_export_kwh: string;
  export_credit_rate_pkr_per_kwh: string;
  gross_retail_import_bill_pkr: string;
  export_credit_pkr: string;
  net_payable_after_credits_pkr: string;
  closing_credit_carryforward_pkr: string;
}

interface ProsumerCompareDto {
  grandfathered: SettlementDto;
  net_billing_2026: SettlementDto;
  grandfathered_advantage_pkr: string;
}

export function estimateBody(request: BillEstimateRequest) {
  return {
    category: request.category,
    sanctioned_load_kw: request.sanctionedLoadKw,
    current_kwh: request.currentKwh,
    peak_kwh: request.peakKwh,
    off_peak_kwh: request.offPeakKwh,
    fpa_reference_2m_prior_kwh: request.fpaReference2mPriorKwh,
    include_electricity_duty: request.includeElectricityDuty,
    is_atl_filer: request.isAtlFiler,
  };
}

export function compareBody(request: ProsumerCompareRequest) {
  return {
    sanctioned_load_kw: request.sanctionedLoadKw,
    gross_peak_import_kwh: request.grossPeakImportKwh,
    gross_off_peak_import_kwh: request.grossOffPeakImportKwh,
    gross_export_kwh: request.grossExportKwh,
    fpa_reference_2m_prior_kwh: request.fpaReference2mPriorKwh,
    include_electricity_duty: request.includeElectricityDuty,
    is_atl_filer: request.isAtlFiler,
  };
}

/** Line-item keys stay snake_case: the view-model labels them by the backend's exact names. */
export function toBillEstimate(dto: BillEstimateDto): BillEstimate {
  return {
    category: dto.category as TariffCategory,
    slabId: dto.slab_id,
    currentTotalKwh: dto.current_total_kwh,
    lineItems: dto.line_items,
    totalPayablePkr: dto.total_payable_pkr,
    totalPayableRoundedRupeePkr: dto.total_payable_rounded_rupee_pkr,
    effectiveAllInRatePkrPerKwh: dto.effective_all_in_rate_pkr_per_kwh,
  };
}

function toSettlement(dto: SettlementDto): ProsumerSettlement {
  return {
    regime: dto.regime as ProsumerRegime,
    netBilledPeakImportKwh: dto.net_billed_peak_import_kwh,
    netBilledOffPeakImportKwh: dto.net_billed_off_peak_import_kwh,
    netSurplusExportKwh: dto.net_surplus_export_kwh,
    exportCreditRatePkrPerKwh: dto.export_credit_rate_pkr_per_kwh,
    grossRetailImportBillPkr: dto.gross_retail_import_bill_pkr,
    exportCreditPkr: dto.export_credit_pkr,
    netPayableAfterCreditsPkr: dto.net_payable_after_credits_pkr,
    closingCreditCarryforwardPkr: dto.closing_credit_carryforward_pkr,
  };
}

export function toProsumerComparison(dto: ProsumerCompareDto): ProsumerComparison {
  return {
    grandfathered: toSettlement(dto.grandfathered),
    netBilling2026: toSettlement(dto.net_billing_2026),
    grandfatheredAdvantagePkr: dto.grandfathered_advantage_pkr,
  };
}

export async function fetchBillEstimate(request: BillEstimateRequest): Promise<BillEstimate> {
  return toBillEstimate(
    await apiFetch<BillEstimateDto>('/api/v2/bill/estimate', {
      method: 'POST',
      body: estimateBody(request),
    }),
  );
}

export async function fetchProsumerComparison(
  request: ProsumerCompareRequest,
): Promise<ProsumerComparison> {
  return toProsumerComparison(
    await apiFetch<ProsumerCompareDto>('/api/v2/prosumer/compare', {
      method: 'POST',
      body: compareBody(request),
    }),
  );
}
