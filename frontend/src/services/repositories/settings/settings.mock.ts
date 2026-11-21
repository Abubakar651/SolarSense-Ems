import type { SettingsData } from '@/types/domain/settings';
import { shortDate } from '@/lib/dates';
import { DEFAULT_REGIME, DEFAULT_TARIFF_CATEGORY, MIN_RESERVE_PCT } from '@/lib/tariff';
import { SAMPLE_SITE } from '../../mock/constants';
import { LAST_READING, STATION } from '../../mock/lhr-res-01';
import { NOTIFICATION_LABELS } from './notification-labels';
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
    inverterHost: '',
    syncStatus: `Last reading ${shortDate(LAST_READING.slice(0, 10))}, ${LAST_READING.slice(11)}`,
    stationCode: STATION.id,
  },
  battery: {
    capacityKwh: SAMPLE_SITE.batteryCapacityKwh,
    reservePct: Math.max(
      MIN_RESERVE_PCT,
      Math.round((SAMPLE_SITE.reserveFloorKwh / SAMPLE_SITE.batteryCapacityKwh) * 100),
    ),
  },
  blackouts: [],
  // Values from docs/station_profile_lhr_res_01.json.
  tariff: {
    category: DEFAULT_TARIFF_CATEGORY,
    regime: DEFAULT_REGIME,
    sanctionedLoadKw: '10',
    isAtlFiler: true,
    includeElectricityDuty: false,
    isProtectedConsumer: false,
  },
  notifications: [
    { key: 'grid_outage', label: NOTIFICATION_LABELS.grid_outage, inApp: true, email: true },
    { key: 'outage_risk', label: NOTIFICATION_LABELS.outage_risk, inApp: true, email: true },
    { key: 'peak_soon', label: NOTIFICATION_LABELS.peak_soon, inApp: true, email: false },
    { key: 'panels_dirty', label: NOTIFICATION_LABELS.panels_dirty, inApp: true, email: true },
    {
      key: 'inverter_offline',
      label: NOTIFICATION_LABELS.inverter_offline,
      inApp: true,
      email: true,
    },
    { key: 'weekly_digest', label: NOTIFICATION_LABELS.weekly_digest, inApp: false, email: true },
  ],
};

export const settingsMock: SettingsRepository = {
  async getSettings() {
    return structuredClone(SAMPLE_SETTINGS);
  },
};
