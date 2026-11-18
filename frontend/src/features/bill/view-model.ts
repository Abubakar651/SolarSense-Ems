import type { TariffCategory } from '@/lib/tariff';
import type {
  BillEstimate,
  BillEstimateRequest,
  ProsumerCompareRequest,
  ProsumerComparison,
  ProsumerSettlement,
} from '@/types/domain/tariff';

/** "12345.5" -> "PKR 12,345.5", "-250.00" -> "-PKR 250.00". Digits stay as the backend sent them. */
export function formatPkr(amount: string): string {
  const negative = amount.startsWith('-');
  const [whole = '0', fraction] = amount.replace('-', '').split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${negative ? '-' : ''}PKR ${grouped}${fraction === undefined ? '' : `.${fraction}`}`;
}

/** Names of the bill lines the backend returns (_PKR_LINE_FIELDS in src/api/main.py). */
const LINE_LABELS: Record<string, string> = {
  peak_energy_charges_pkr: 'Peak energy',
  off_peak_energy_charges_pkr: 'Off-peak energy',
  variable_energy_charges_pkr: 'Energy charges',
  fixed_charges_pkr: 'Fixed charges',
  qta_pkr: 'Quarterly tariff adjustment',
  fc_surcharge_pkr: 'Financing cost surcharge',
  electricity_duty_current_pkr: 'Electricity duty',
  current_pre_gst_subtotal_pkr: 'Subtotal before GST',
  gst_on_current_bill_pkr: 'GST',
  fpa_base_pkr: 'Fuel price adjustment',
  ed_and_gst_on_fpa_pkr: 'Duty and GST on fuel adjustment',
  ptv_fee_pkr: 'PTV fee',
  subtotal_before_income_tax_pkr: 'Subtotal before income tax',
  section_235_income_tax_pkr: 'Income tax (section 235)',
};

/** "some_new_charge_pkr" -> "Some new charge", for a line the backend adds later. */
function humanise(key: string): string {
  const words = key.replace(/_pkr$/, '').replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function estimateRows(estimate: BillEstimate): string[][] {
  return Object.entries(estimate.lineItems).map(([key, amount]) => [
    LINE_LABELS[key] ?? humanise(key),
    formatPkr(amount),
  ]);
}

const SETTLEMENT_ROWS: { label: string; read: (s: ProsumerSettlement) => string }[] = [
  { label: 'Peak units billed', read: (s) => `${s.netBilledPeakImportKwh} kWh` },
  { label: 'Off-peak units billed', read: (s) => `${s.netBilledOffPeakImportKwh} kWh` },
  { label: 'Surplus exported', read: (s) => `${s.netSurplusExportKwh} kWh` },
  { label: 'Export credit rate', read: (s) => `${formatPkr(s.exportCreditRatePkrPerKwh)}/kWh` },
  { label: 'Import bill', read: (s) => formatPkr(s.grossRetailImportBillPkr) },
  { label: 'Export credit', read: (s) => formatPkr(s.exportCreditPkr) },
  { label: 'Payable after credits', read: (s) => formatPkr(s.netPayableAfterCreditsPkr) },
  { label: 'Credit carried forward', read: (s) => formatPkr(s.closingCreditCarryforwardPkr) },
];

/** One row per figure: label, net metering, net billing. */
export function comparisonRows(comparison: ProsumerComparison): string[][] {
  return SETTLEMENT_ROWS.map(({ label, read }) => [
    label,
    read(comparison.grandfathered),
    read(comparison.netBilling2026),
  ]);
}

/** The one-line verdict; a positive advantage means net metering costs less. */
export function advantageSentence(comparison: ProsumerComparison): string {
  const amount = comparison.grandfatheredAdvantagePkr;
  const value = Number(amount);
  if (value === 0) return 'Both arrangements cost the same this month.';
  const [name, other] =
    value > 0 ? ['Net metering', 'net billing'] : ['Net billing', 'net metering'];
  return `${name} costs ${formatPkr(amount.replace('-', ''))} less than ${other} this month.`;
}

const numberField = (data: FormData, name: string): number => {
  const raw = String(data.get(name) ?? '').trim();
  return raw === '' ? 0 : Number(raw);
};

/** Reads the bill estimate form; empty unit fields count as 0, as the backend defaults them. */
export function readEstimateForm(form: HTMLFormElement): BillEstimateRequest {
  const data = new FormData(form);
  return {
    category: String(data.get('bill-cat')) as TariffCategory,
    sanctionedLoadKw: numberField(data, 'bill-load'),
    currentKwh: numberField(data, 'bill-kwh'),
    peakKwh: numberField(data, 'bill-peak'),
    offPeakKwh: numberField(data, 'bill-off'),
    fpaReference2mPriorKwh: numberField(data, 'bill-fpa'),
    includeElectricityDuty: data.has('bill-duty'),
    isAtlFiler: data.has('bill-atl'),
  };
}

export function readCompareForm(form: HTMLFormElement): ProsumerCompareRequest {
  const data = new FormData(form);
  return {
    sanctionedLoadKw: numberField(data, 'cmp-load'),
    grossPeakImportKwh: numberField(data, 'cmp-peak'),
    grossOffPeakImportKwh: numberField(data, 'cmp-off'),
    grossExportKwh: numberField(data, 'cmp-exp'),
    fpaReference2mPriorKwh: numberField(data, 'cmp-fpa'),
    includeElectricityDuty: data.has('cmp-duty'),
    isAtlFiler: data.has('cmp-atl'),
  };
}

/**
 * Time-of-use bills are priced from peak and off-peak units only; every other category from total
 * units (calculate_monthly_bill in src/optimizer/lesco_2026_tariff_and_dispatch.py).
 */
export const usesPeakSplit = (category: TariffCategory): boolean => category === 'TOU_A1B';
