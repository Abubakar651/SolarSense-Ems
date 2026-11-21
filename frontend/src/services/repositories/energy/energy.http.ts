import { cache } from 'react';
import { clockInKarachi } from '@/lib/dates';
import type { DayPlan, DayPlanResult } from '@/types/domain/energy';
import { ApiError, apiGet, apiPostRead } from '../../http/client';
import type { LivePlanDto, OptimizeDto } from '../../http/dto';
import { energyResult, fetchEnergyHistory, fetchLatestDataDay } from '../insights.http';
import { toDayCurve, type DayCurveDto } from './day-curve';
import { toEnergyHistory } from './energy-history';
import { settingsHttp } from '../settings/settings.http';
import type { EnergyRepository } from './energy.repository';

/** The hours the optimizer priced at the peak rate, as [start, end). The tariff engine flags a window every month. */
function peakWindow(dto: OptimizeDto): { start: number; end: number } {
  const peakHours = dto.is_peak.flatMap((flag, hour) => (flag === 1 ? [hour] : []));
  const first = peakHours[0];
  const last = peakHours[peakHours.length - 1];
  if (first === undefined || last === undefined) {
    throw new Error('The optimizer returned a day without peak hours');
  }
  return { start: first, end: last + 1 };
}

interface Battery {
  capacityKwh: number;
  reserveFloorKwh: number;
}

/**
 * The optimizer's 24-hour dispatch, in UI terms. The battery level is a percentage of the battery
 * the dispatch was solved for.
 */
function toPlan(
  dto: OptimizeDto,
  date: string,
  battery: Battery,
): Omit<DayPlan, 'isSample' | 'clockStart' | 'forecast' | 'initialSocAssumed'> {
  const capacity = battery.capacityKwh;
  const peak = peakWindow(dto);
  return {
    sampleDate: date,
    // The all-in rates the backend's tariff engine priced the plan at, for the user's own tariff.
    tariff: {
      peakPkr: Number(dto.peak_import_rate_pkr_per_kwh),
      offPeakPkr: Number(dto.off_peak_import_rate_pkr_per_kwh),
      exportPkr: Number(dto.export_rate_used_pkr_per_kwh),
    },
    solar: dto.solar_kw,
    load: dto.load_kw,
    soc: dto.soc_kwh.slice(1).map((kwh) => Math.round((kwh / capacity) * 100)),
    grid: dto.p_grid_import_kw,
    charge: dto.p_ch_kw,
    peakStartHour: peak.start,
    peakEndHour: peak.end,
    batteryCapacityKwh: capacity,
    reserveFloorKwh: battery.reserveFloorKwh,
  };
}

/**
 * Today's plan on live forecasts, solved for the user's own battery and array; the clock starts at
 * the real time in Lahore.
 */
export function toLiveDayPlan(dto: LivePlanDto, now: Date): DayPlan {
  return {
    ...toPlan(dto, dto.date, {
      capacityKwh: dto.battery_capacity_kwh,
      reserveFloorKwh: dto.reserve_floor_kwh,
    }),
    isSample: false,
    clockStart: clockInKarachi(now),
    forecast: { loggedHistoryHours: dto.history_logged_hours, historyHours: dto.history_hours },
    initialSocAssumed: dto.initial_soc_assumed,
  };
}

/**
 * A replay of the station's recorded day, for the station owner only (the backend solves it for the
 * owner's own battery and reserve). The clock is the real time in Lahore.
 */
export function toRecordedDayPlan(
  dto: OptimizeDto,
  date: string,
  battery: Battery,
  now: Date,
): DayPlan {
  return {
    ...toPlan(dto, date, battery),
    isSample: true,
    clockStart: clockInKarachi(now),
    forecast: null,
    initialSocAssumed: false,
  };
}

/**
 * The plan is shown by the app shell and by the page; cache() solves it once per render. While the site
 * has logged none of the history the forecast needs (409) the plan is "collecting". Without a weather
 * forecast (503) the station owner gets a replay of their own recorded day, labelled as sample data;
 * every other home gets "unavailable", never another home's data.
 */
const fetchDayPlan = cache(async (): Promise<DayPlanResult> => {
  const settings = await settingsHttp.getSettings();
  const tariff = {
    regime: settings.tariff.regime,
    is_protected_consumer: settings.tariff.isProtectedConsumer,
    include_electricity_duty: settings.tariff.includeElectricityDuty,
  };
  try {
    const dto = await apiPostRead<LivePlanDto>('/api/v2/plan/today', tariff);
    return { status: 'ready', plan: toLiveDayPlan(dto, new Date()) };
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
    if (error.status === 409) return { status: 'collecting' };
    if (error.status !== 503) throw error;
  }
  if (settings.site.stationCode === null) return { status: 'unavailable' };
  const date = await fetchLatestDataDay();
  const dto = await apiPostRead<OptimizeDto>('/api/v2/optimize', { date_str: date, ...tariff });
  const { capacityKwh, reservePct } = settings.battery;
  const battery = { capacityKwh, reserveFloorKwh: (capacityKwh * reservePct) / 100 };
  return { status: 'ready', plan: toRecordedDayPlan(dto, date, battery, new Date()) };
});

export const energyHttp: EnergyRepository = {
  getDayPlan: fetchDayPlan,
  async getEnergyHistory() {
    const dto = await fetchEnergyHistory();
    return energyResult(dto, () => toEnergyHistory(dto));
  },
  async getDayCurve(date) {
    const query = date === undefined ? '' : `?date=${encodeURIComponent(date)}`;
    try {
      return toDayCurve(await apiGet<DayCurveDto>(`/api/insights/day-curve${query}`));
    } catch (error) {
      // A date the site has no curve for falls back to its latest day.
      if (date !== undefined && error instanceof ApiError && error.status === 404) {
        return toDayCurve(await apiGet<DayCurveDto>('/api/insights/day-curve'));
      }
      throw error;
    }
  },
};
