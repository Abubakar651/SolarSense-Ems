export const ONBOARDING_STEPS = ['Site', 'System', 'Tariff', 'Review'] as const;
export const LAST_STEP = ONBOARDING_STEPS.length - 1;

export interface ReviewRow {
  label: string;
  value: string;
}

const orDash = (value: string | undefined) => value || '—';

/** The summary shown on the last step, built from the values entered in the earlier steps. */
export function reviewRows(values: Record<string, string>): ReviewRow[] {
  const v = (id: string) => orDash(values[id]);
  return [
    { label: 'Site', value: v('ob-site') },
    { label: 'Address', value: `${v('ob-addr')}, ${v('ob-city')}` },
    { label: 'Solar', value: `${v('ob-pv')} kWp` },
    { label: 'Battery', value: `${v('ob-bat')} kWh` },
    { label: 'Inverter', value: `${values['ob-inv'] ?? ''} · ${v('ob-sn')}` },
    {
      label: 'Tariff',
      value: `Peak ${v('ob-peak')} · Off-peak ${v('ob-off')} · Export ${v('ob-exp')} PKR/kWh`,
    },
  ];
}

/** Text fields from a submitted form as a plain record (files are not expected here). */
export function formValues(form: HTMLFormElement): Record<string, string> {
  return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, String(value)]));
}
