export type PriorityMode = 'comfort' | 'balanced' | 'savings';

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
    reservePct: number;
    priority: PriorityMode;
    neverChargeAtPeak: boolean;
    overnightGridCharge: boolean;
    exportExtra: boolean;
    chargeFrom: string;
    chargeTo: string;
  };
  blackouts: BlackoutWindow[];
  tariff: {
    plan: string;
    peakStart: string;
    peakEnd: string;
    peakRate: string;
    offPeakRate: string;
    exportRate: string;
  };
  notifications: { label: string; inApp: boolean; email: boolean }[];
}
