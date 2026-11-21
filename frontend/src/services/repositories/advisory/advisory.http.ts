import type { Advisory, AdvisoryResult } from '@/types/domain/advisory';
import { ApiError, apiPostRead } from '../../http/client';
import type { DailyBriefDto } from '../../http/dto';
import { settingsHttp } from '../settings/settings.http';
import type { AdvisoryRepository } from './advisory.repository';

export function toAdvisory(dto: DailyBriefDto): Advisory {
  const metric = (key: string): number | null => dto.key_metrics[key] ?? null;
  return {
    date: dto.date,
    headline: dto.headline,
    dispatchArbitrageBrief: dto.dispatch_arbitrage_brief,
    blackoutResilienceBrief: dto.blackout_resilience_brief,
    soilingMaintenanceBrief: dto.soiling_maintenance_brief,
    recommendedActions: dto.recommended_actions,
    keyMetrics: {
      solarGenerationKwh: metric('solar_generation_kwh') ?? 0,
      householdLoadKwh: metric('household_load_kwh') ?? 0,
      gridImportKwh: metric('grid_import_kwh') ?? 0,
      netMeteringExportKwh: metric('net_metering_export_kwh'),
      exportRevenuePkr: metric('export_revenue_pkr'),
      peakBatteryDischargeKwh: metric('peak_battery_discharge_kwh') ?? 0,
      outageHours: metric('outage_hours') ?? 0,
      netSavingsPkr: metric('net_savings_pkr'),
      soilingLossKwh: metric('soiling_loss_kwh'),
      netCleaningBenefitPkr: metric('net_cleaning_benefit_pkr'),
    },
    generationMode: dto.generation_mode,
    isSample: false,
  };
}

/**
 * Today's brief for the user's own site, written by the backend from the same live plan as the plan
 * screen, at the user's tariff settings. Without a weather forecast (503) there is no plan to write
 * about, so the brief is "unavailable"; it never falls back to sample text.
 */
export const advisoryHttp: AdvisoryRepository = {
  async getAdvisory(): Promise<AdvisoryResult> {
    const settings = await settingsHttp.getSettings();
    const tariff = {
      regime: settings.tariff.regime,
      is_protected_consumer: settings.tariff.isProtectedConsumer,
      include_electricity_duty: settings.tariff.includeElectricityDuty,
    };
    try {
      const dto = await apiPostRead<DailyBriefDto>('/api/agent/advisory/today', tariff);
      return { status: 'ready', advisory: toAdvisory(dto) };
    } catch (error) {
      // 409: the site has logged too little for today's plan yet, so there is nothing to write about either.
      if (error instanceof ApiError && (error.status === 503 || error.status === 409)) {
        return { status: 'unavailable' };
      }
      throw error;
    }
  },
};
