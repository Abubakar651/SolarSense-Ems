export type PriorityMode = 'comfort' | 'balanced' | 'savings';

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
