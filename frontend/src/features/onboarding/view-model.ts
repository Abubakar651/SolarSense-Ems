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
