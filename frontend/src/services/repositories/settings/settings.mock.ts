import type { SettingsData } from '@/types/domain/settings';
import { shortDate } from '@/lib/dates';
import { pad } from '@/lib/format';
import { SAMPLE_SITE } from '../../mock/constants';
import { LAST_READING, STATION, TARIFF } from '../../mock/lhr-res-01';
import type { SettingsRepository } from './settings.repository';

const SAMPLE_SETTINGS: SettingsData = {
  profile: {
    name: 'Zaeem',
    initials: 'Z',
    phone: '',
    email: 'zaeem@example.com',
  },
  site: {
    name: STATION.id,
    city: STATION.city,
    address: STATION.area,
    solarKwp: STATION.solarKwp.toFixed(2),
    batteryKwh: STATION.batteryKwh.toFixed(2),
    inverter: STATION.inverter,
    serial: STATION.serial,
    syncStatus: `Last reading ${shortDate(LAST_READING.slice(0, 10))}, ${LAST_READING.slice(11)}`,
  },
  battery: {
    capacityKwh: SAMPLE_SITE.batteryCapacityKwh,
    reservePct: Math.round((SAMPLE_SITE.reserveFloorKwh / SAMPLE_SITE.batteryCapacityKwh) * 100),
    priority: 'balanced',
    neverChargeAtPeak: true,
    overnightGridCharge: true,
    exportExtra: true,
    chargeFrom: '23:00',
    chargeTo: '05:00',
  },
  tariff: {
    plan: 'Time-of-use (peak / off-peak)',
    peakStart: `${pad(TARIFF.peakStartHour)}:00`,
    peakEnd: `${pad(TARIFF.peakEndHour)}:00`,
    peakRate: TARIFF.peakPkrPerKwh.toFixed(2),
    offPeakRate: TARIFF.offPeakPkrPerKwh.toFixed(2),
    exportRate: TARIFF.exportPkrPerKwh.toFixed(2),
  },
  notifications: [
    { label: 'Grid outage starts or ends', inApp: true, email: true },
    { label: 'High outage risk tonight', inApp: true, email: true },
    { label: 'Peak hours starting soon', inApp: true, email: false },
    { label: 'Panels need cleaning', inApp: true, email: true },
    { label: 'Inverter offline', inApp: true, email: true },
    { label: 'Weekly savings digest', inApp: false, email: true },
  ],
};

export const settingsMock: SettingsRepository = {
  async getSettings() {
    return structuredClone(SAMPLE_SETTINGS);
  },
};
