import { redirect } from 'next/navigation';
import { initials } from '@/lib/format';
import type { ProsumerRegime, TariffCategory } from '@/lib/tariff';
import type { NotificationKey, SettingsData } from '@/types/domain/settings';
import { ApiError, apiGet } from '../../http/client';
import type { SettingsDto } from '../../http/dto';
import { NOTIFICATION_LABELS } from './notification-labels';
import type { SettingsRepository } from './settings.repository';

function isNotificationKey(key: string): key is NotificationKey {
  return key in NOTIFICATION_LABELS;
}

/** API settings -> the shape the Settings screen edits (kWp/kWh as fixed-2 strings, like the inputs). */
export function toSettingsData(dto: SettingsDto): SettingsData {
  return {
    profile: {
      name: dto.profile.name,
      initials: initials(dto.profile.name),
      phone: dto.profile.phone,
      email: dto.profile.email,
    },
    site: {
      name: dto.site.name,
      city: dto.site.city,
      address: dto.site.address,
      solarKwp: dto.site.pv_kwp.toFixed(2),
      batteryKwh: dto.site.battery_kwh.toFixed(2),
      inverter: dto.site.inverter_make,
      serial: dto.site.inverter_serial,
      inverterHost: dto.site.inverter_host ?? '',
      syncStatus: dto.site.station_code
        ? `Includes the recorded history of station ${dto.site.station_code}`
        : 'Uses your own inverter’s data',
      stationCode: dto.site.station_code,
    },
    battery: { capacityKwh: dto.site.battery_kwh, reservePct: dto.reserve_pct },
    blackouts: dto.blackouts.map(({ start, end }) => ({ start, end })),
    tariff: {
      category: dto.tariff.category as TariffCategory,
      regime: dto.tariff.regime as ProsumerRegime,
      sanctionedLoadKw: String(dto.tariff.sanctioned_load_kw),
      isAtlFiler: dto.tariff.is_atl_filer,
      includeElectricityDuty: dto.tariff.include_electricity_duty,
      isProtectedConsumer: dto.tariff.is_protected_consumer,
    },
    // Keys the UI doesn't know yet (a newer backend) are skipped rather than shown unlabeled.
    notifications: dto.notifications.flatMap(({ key, in_app, email }) =>
      isNotificationKey(key)
        ? [{ key, label: NOTIFICATION_LABELS[key], inApp: in_app, email }]
        : [],
    ),
  };
}

export const settingsHttp: SettingsRepository = {
  async getSettings() {
    try {
      return toSettingsData(await apiGet<SettingsDto>('/api/settings', '/settings'));
    } catch (error) {
      if (error instanceof ApiError && error.code === 'site_not_found') redirect('/onboarding');
      throw error;
    }
  },
};
