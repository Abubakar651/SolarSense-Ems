import { PROSUMER_REGIMES, TARIFF_CATEGORIES } from '@/lib/tariff';

export const ONBOARDING_STEPS = ['Site', 'System', 'Tariff', 'Review'] as const;
export const LAST_STEP = ONBOARDING_STEPS.length - 1;

export interface ReviewRow {
  label: string;
  value: string;
}

const orDash = (value: string | undefined) => value || '—';

/** "Time-of-use A-1(b) · 10 kW · Export 25.32 PKR/kWh", with a dash for anything not chosen. */
function tariffSummary(values: Record<string, string>): string {
  const category = TARIFF_CATEGORIES.find((c) => c.id === values['ob-cat']);
  const regime = PROSUMER_REGIMES.find((r) => r.id === values['ob-reg']);
  const export_ = regime ? `${regime.exportPkrPerKwh.toFixed(2)} PKR/kWh` : '—';
  return `${category?.label ?? '—'} · ${orDash(values['ob-load'])} kW · Export ${export_}`;
}

/** The summary shown on the last step, built from the values entered in the earlier steps. */
export function reviewRows(values: Record<string, string>): ReviewRow[] {
  const v = (id: string) => orDash(values[id]);
  return [
    { label: 'Site', value: v('ob-site') },
    { label: 'Address', value: `${v('ob-addr')}, ${v('ob-city')}` },
    { label: 'Solar', value: `${v('ob-pv')} kWp` },
    { label: 'Battery', value: `${v('ob-bat')} kWh` },
    { label: 'Inverter', value: `${values['ob-inv'] ?? ''} · ${v('ob-sn')}` },
    { label: 'Tariff', value: tariffSummary(values) },
  ];
}

/** Text fields from a submitted form as a plain record (files are not expected here). */
export function formValues(form: HTMLFormElement): Record<string, string> {
  return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, String(value)]));
}

/** Body of POST /api/site; mirrors OnboardingRequest in src/api/account_schemas.py. */
export interface OnboardingRequest {
  name: string;
  address: string;
  city: string;
  pv_kwp: number;
  battery_kwh: number;
  inverter_make: 'GoodWe' | 'Other';
  inverter_serial: string;
  tariff_category: string;
  prosumer_regime: string;
  sanctioned_load_kw: number;
}

/** The wizard's values as the API expects them ("Other (tell us later)" is stored as "Other"). */
export function toOnboardingRequest(values: Record<string, string>): OnboardingRequest {
  const v = (id: string) => (values[id] ?? '').trim();
  return {
    name: v('ob-site'),
    address: v('ob-addr'),
    city: v('ob-city'),
    pv_kwp: Number(v('ob-pv')),
    battery_kwh: Number(v('ob-bat')),
    inverter_make: v('ob-inv') === 'GoodWe' ? 'GoodWe' : 'Other',
    inverter_serial: v('ob-sn'),
    tariff_category: v('ob-cat'),
    prosumer_regime: v('ob-reg'),
    sanctioned_load_kw: Number(v('ob-load')),
  };
}
