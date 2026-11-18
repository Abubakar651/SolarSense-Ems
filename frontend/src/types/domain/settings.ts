import type { ProsumerRegime, TariffCategory } from '@/lib/tariff';

/** A daily window, as 24-hour "HH:MM", when the user knows the grid will be off. `end` may be earlier than `start` (crosses midnight). */
export interface BlackoutWindow {
  start: string;
  end: string;
}

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
    syncStatus: string;
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
  notifications: { label: string; inApp: boolean; email: boolean }[];
}
