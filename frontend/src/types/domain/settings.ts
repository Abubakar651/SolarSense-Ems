import type { ProsumerRegime, TariffCategory } from '@/lib/tariff';

/** A daily window, as 24-hour "HH:MM", when the user knows the grid will be off. `end` may be earlier than `start` (crosses midnight). */
export interface BlackoutWindow {
  start: string;
  end: string;
}

/** Stable id of an alert type; the backend stores notification choices under these keys. */
export type NotificationKey =
  | 'grid_outage'
  | 'outage_risk'
  | 'peak_soon'
  | 'panels_dirty'
  | 'inverter_offline'
  | 'weekly_digest';

export interface SettingsData {
  profile: { name: string; initials: string; phone: string; email: string };
  site: {
    name: string;
    city: string;
    address: string;
    solarKwp: string;
    batteryKwh: string;
    inverter: string;
    serial: string;
    /** The inverter's IP address on the home network; "" when not connected. */
    inverterHost: string;
    syncStatus: string;
    /** The recorded station dataset this site owns (only the station owner's site); null for every other. */
    stationCode: string | null;
  };
  battery: {
    capacityKwh: number;
    /** Share of the battery held back for outages; never below the 15% inverter floor. */
    reservePct: number;
  };
  blackouts: BlackoutWindow[];
  /** The per-customer fields of the backend's StationProfile (docs/station_profile_lhr_res_01.json). */
  tariff: {
    category: TariffCategory;
    regime: ProsumerRegime;
    sanctionedLoadKw: string;
    isAtlFiler: boolean;
    includeElectricityDuty: boolean;
    isProtectedConsumer: boolean;
  };
  notifications: { key: NotificationKey; label: string; inApp: boolean; email: boolean }[];
}
