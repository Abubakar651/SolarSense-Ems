import { DISCHARGE_EFFICIENCY } from '@/lib/backup-hours';
import type { BlackoutWindow, NotificationKey, SettingsData } from '@/types/domain/settings';

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
    's-host': site.inverterHost,
    reserve: String(battery.reservePct),
    't-cat': tariff.category,
    't-reg': tariff.regime,
    't-load': tariff.sanctionedLoadKw,
    't-atl': tariff.isAtlFiler,
    't-duty': tariff.includeElectricityDuty,
    't-prot': tariff.isProtectedConsumer,
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

/**
 * What the reserve holds: hours of backup at the home's own overnight usage (from today's plan), or just
 * the energy while there is no plan to know that usage from.
 */
export function reserveHint(
  reservePct: number,
  capacityKwh: number,
  overnightLoadKw: number | null,
): string {
  const reserveKwh = (capacityKwh * reservePct) / 100;
  if (overnightLoadKw === null || overnightLoadKw <= 0) {
    return `Holds ${reserveKwh.toFixed(1)} kWh for outages, held back from daily savings.`;
  }
  const hours = (reserveKwh * DISCHARGE_EFFICIENCY) / overnightLoadKw;
  return `About ${hours.toFixed(1)} hours of backup at your usual overnight usage, held back from daily savings.`;
}

const MINUTES_PER_DAY = 24 * 60;

function minutesOfDay(time: string): number {
  const [hours = 0, minutes = 0] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

/** Why a blackout window can't be added, or null when it can. */
export function blackoutError(
  start: string,
  end: string,
  existing: readonly BlackoutWindow[],
): string | null {
  if (!start || !end) return 'Choose a start and an end time.';
  if (start === end) return 'Start and end must be different times.';
  if (existing.some((window) => window.start === start && window.end === end)) {
    return 'That blackout is already listed.';
  }
  return null;
}

/** Length of a window such as "1 h 30 min"; a window ending before it starts runs past midnight. */
export function blackoutLength(start: string, end: string): string {
  const total = (minutesOfDay(end) - minutesOfDay(start) + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  return [hours > 0 && `${hours} h`, minutes > 0 && `${minutes} min`].filter(Boolean).join(' ');
}

/** True when both lists hold the same windows in the same order. */
export function blackoutsEqual(
  a: readonly BlackoutWindow[],
  b: readonly BlackoutWindow[],
): boolean {
  return a.length === b.length && a.every((w, i) => w.start === b[i]?.start && w.end === b[i]?.end);
}

/** Body of PUT /api/settings; mirrors SettingsUpdate in src/api/account_schemas.py. */
export interface SettingsUpdate {
  profile: { name: string; phone: string };
  site: {
    name: string;
    city: string;
    address: string;
    pv_kwp: number;
    battery_kwh: number;
    inverter_make: string;
    /** Null disconnects the inverter. */
    inverter_host: string | null;
  };
  reserve_pct: number;
  blackouts: BlackoutWindow[];
  tariff: {
    category: string;
    regime: string;
    sanctioned_load_kw: number;
    is_atl_filer: boolean;
    include_electricity_duty: boolean;
    is_protected_consumer: boolean;
  };
  notifications: { key: NotificationKey; in_app: boolean; email: boolean }[];
}

/** The whole form, as the API expects it on Save. Number fields are sent as numbers. */
export function toSettingsUpdate(
  values: SettingsValues,
  blackouts: readonly BlackoutWindow[],
  notifications: SettingsData['notifications'],
): SettingsUpdate {
  const text = (key: string) => String(values[key] ?? '').trim();
  const flag = (key: string) => values[key] === true;
  return {
    profile: { name: text('p-name'), phone: text('p-phone') },
    site: {
      name: text('s-name'),
      city: text('s-city'),
      address: text('s-addr'),
      pv_kwp: Number(text('s-pv')),
      battery_kwh: Number(text('s-bat')),
      inverter_make: text('s-inv'),
      inverter_host: text('s-host') || null,
    },
    reserve_pct: Number(text('reserve')),
    blackouts: blackouts.map(({ start, end }) => ({ start, end })),
    tariff: {
      category: text('t-cat'),
      regime: text('t-reg'),
      sanctioned_load_kw: Number(text('t-load')),
      is_atl_filer: flag('t-atl'),
      include_electricity_duty: flag('t-duty'),
      is_protected_consumer: flag('t-prot'),
    },
    notifications: notifications.map(({ key }, index) => ({
      key,
      in_app: flag(`notify-${index}-app`),
      email: flag(`notify-${index}-email`),
    })),
  };
}
