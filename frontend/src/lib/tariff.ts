/**
 * LESCO tariff rules as the backend implements them. The UI offers exactly these options so a screen
 * can later be wired to the API without remapping.
 */

export interface PeakWindow {
  season: 'Winter' | 'Spring' | 'Summer' | 'Autumn';
  /** Months the window applies to, as numbers (1 = January). */
  months: readonly number[];
  /** Hour the peak starts and the hour it ends (exclusive), local time. */
  startHour: number;
  endHour: number;
}

/** Base ToU A-1(b) rates (PKR/kWh), topic B of the same file. Bills add GST, FC, QTA and FCA on top. */
export const TOU_RATES = { peakPkr: 46.85, offPeakPkr: 34.53 } as const;

/** Mirrors ProsumerRegime2026 in src/optimizer/lesco_2026_tariff_and_dispatch.py. */
export type ProsumerRegime =
  'GRANDFATHERED_NET_METERING' | 'NET_BILLING_2026' | 'SINGLE_PHASE_SLAB_ZERO_EXPORT';

export interface RegimeInfo {
  id: ProsumerRegime;
  label: string;
  /** What exporting earns, in plain words. */
  summary: string;
  /** Credit per surplus kWh sent to the grid (PKR). */
  exportPkrPerKwh: number;
}

/**
 * Export credit per regime, topic D of the tariff config: NAPPP 25.32 (grandfathered, S.R.O. 547(I)/2026),
 * NAEPP 8.13 (net billing, S.R.O. 251(I)/2026) and no export on a single-phase slab connection.
 * Under net metering, exported units first cancel off-peak imports one for one.
 */
export const PROSUMER_REGIMES: readonly RegimeInfo[] = [
  {
    id: 'GRANDFATHERED_NET_METERING',
    label: 'Net metering (agreement before 9 Feb 2026)',
    summary: 'Exports first cancel off-peak imports 1:1; the surplus is paid at the rate below.',
    exportPkrPerKwh: 25.32,
  },
  {
    id: 'NET_BILLING_2026',
    label: 'Net billing (agreement from 9 Feb 2026)',
    summary: 'No 1:1 netting. Every exported unit is credited at the rate below.',
    exportPkrPerKwh: 8.13,
  },
  {
    id: 'SINGLE_PHASE_SLAB_ZERO_EXPORT',
    label: 'Single-phase slab, no export',
    summary: 'Export is not allowed or metered, so nothing is credited.',
    exportPkrPerKwh: 0,
  },
];

export const DEFAULT_REGIME: ProsumerRegime = 'GRANDFATHERED_NET_METERING';

export function regimeInfo(id: ProsumerRegime): RegimeInfo {
  const info = PROSUMER_REGIMES.find((regime) => regime.id === id);
  if (!info) throw new RangeError(`Unknown regime: ${id}`);
  return info;
}

/** Mirrors the `category` field of BillEstimateRequest in src/api/schemas.py. */
export type TariffCategory = 'LIFELINE' | 'PROTECTED' | 'UNPROTECTED' | 'TOU_A1B' | 'PREPAID_A1C';

export const TARIFF_CATEGORIES: readonly { id: TariffCategory; label: string }[] = [
  { id: 'LIFELINE', label: 'Lifeline (up to 1 kW, 100 units)' },
  { id: 'PROTECTED', label: 'Protected (under 5 kW, 200 units)' },
  { id: 'UNPROTECTED', label: 'Unprotected (under 5 kW)' },
  { id: 'TOU_A1B', label: 'Time-of-use A-1(b)' },
  { id: 'PREPAID_A1C', label: 'Prepaid A-1(c)' },
];

export const DEFAULT_TARIFF_CATEGORY: TariffCategory = 'TOU_A1B';

export function tariffCategoryLabel(id: TariffCategory): string {
  return TARIFF_CATEGORIES.find((category) => category.id === id)?.label ?? id;
}

/** The inverter's hard floor: BESSConfig.station_residential() has min_soc_pct 0.15 (milp_solver.py). */
export const MIN_RESERVE_PCT = 15;
