import type { SettingsData } from '@/types/domain/settings';

export type SettingsValue = string | boolean;
/** Every editable setting, keyed by the id (or name) of its input. */
export type SettingsValues = Record<string, SettingsValue>;

/** Flattens the settings into the form's values. */
export function toFormValues(data: SettingsData): SettingsValues {
  const { profile, site, battery, tariff } = data;
  const values: SettingsValues = {
    'p-name': profile.name,
    'p-phone': profile.phone,
    's-name': site.name,
    's-city': site.city,
    's-addr': site.address,
    's-pv': site.solarKwp,
    's-bat': site.batteryKwh,
    's-inv': site.inverter,
    reserve: String(battery.reservePct),
    prio: battery.priority,
    'rule-peak': battery.neverChargeAtPeak,
    'rule-overnight': battery.overnightGridCharge,
    'rule-export': battery.exportExtra,
    'ch-from': battery.chargeFrom,
    'ch-to': battery.chargeTo,
    't-plan': tariff.plan,
    't-ps': tariff.peakStart,
    't-pe': tariff.peakEnd,
    't-p': tariff.peakRate,
    't-o': tariff.offPeakRate,
    't-e': tariff.exportRate,
  };
  data.notifications.forEach((entry, index) => {
    values[`notify-${index}-app`] = entry.inApp;
    values[`notify-${index}-email`] = entry.email;
  });
  return values;
}

/** True when any value differs from the saved one. */
export function isDirty(values: SettingsValues, saved: SettingsValues): boolean {
  const keys = new Set([...Object.keys(values), ...Object.keys(saved)]);
  return [...keys].some((key) => values[key] !== saved[key]);
}

/** Hours of typical overnight backup the reserve holds (0.9 = usable share of the battery). */
export function reserveHint(reservePct: number, capacityKwh: number): string {
  const hours = (capacityKwh * reservePct) / 100 / 0.9;
  return `About ${hours.toFixed(1)} hours of typical overnight backup, held back from daily savings.`;
}
