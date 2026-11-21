import { cache } from 'react';
import type { Freshness, HistoryResult } from '@/types/domain/history';
import type { MonthlyMeter } from '../mock/lhr-res-01';
import type { DailyEnergy, OutageRecord } from '../mock/lhr-res-01-history';
import type { EnergyRates } from '../mock/valuation';
import { apiFetch, apiGet } from '../http/client';
import type {
  DateBoundsDto,
  EnergyHistoryDto,
  OutageHistoryDto,
  RainForecastDto,
  SoilingHistoryDto,
} from '../http/dto';
import type { SoilingInput } from './panels/panels.mock';

/** API rows -> the record shapes the shared screen builders take (same as the sample data's). */
export function toDailyEnergy(dto: EnergyHistoryDto): DailyEnergy[] {
  return dto.daily.map(
    (d) => [d.date, d.solar_kwh, d.load_kwh, d.import_kwh, d.export_kwh] as const,
  );
}

/**
 * The recorded month ends on the last recorded day. Months after it are summed from the site's own log,
 * so they cover only the days logged in them (a home that started logging on the 18th covers 18 on).
 */
export function toMonthlyMeters(dto: EnergyHistoryDto): MonthlyMeter[] {
  const recordedThrough = dto.recorded_through ?? '';
  const recordedMonth = recordedThrough.slice(0, 7);
  const dayOf = (date: string) => Number(date.slice(8));
  return dto.monthly.map((m) => {
    const meter: MonthlyMeter = {
      month: m.month,
      pvKwh: m.pv_kwh,
      loadKwh: m.load_kwh,
      purchasedKwh: m.purchased_kwh,
      soldKwh: m.sold_kwh,
    };
    if (m.month === recordedMonth) return { ...meter, lastDay: dayOf(recordedThrough) };
    if (m.month < recordedMonth) return meter;
    const logged = dto.daily.filter((d) => d.date.startsWith(m.month) && d.date > recordedThrough);
    const first = logged[0];
    const last = logged[logged.length - 1];
    if (!first || !last) return meter;
    return { ...meter, firstDay: dayOf(first.date), lastDay: dayOf(last.date) };
  });
}

/** The backend tariff engine's rates for the user's own tariff; a history with data always carries them. */
export function toEnergyRates(dto: EnergyHistoryDto): EnergyRates {
  if (!dto.rates) throw new Error('The energy history has no tariff rates');
  return {
    selfConsumedPkrPerKwh: Number(dto.rates.self_consumed_pkr_per_kwh),
    exportPkrPerKwh: Number(dto.rates.export_pkr_per_kwh),
  };
}

export function toOutageRecords(dto: OutageHistoryDto): OutageRecord[] {
  return dto.events.map(
    (e) => [e.date, e.start, e.end, e.minutes, e.energy_kwh, null, e.soc_end_pct] as const,
  );
}

export function toSoilingInput(dto: SoilingHistoryDto): SoilingInput {
  return {
    washDate: dto.wash_date,
    cleanEvent: dto.clean_event,
    asOf: dto.as_of,
    modelPr: dto.model_pr,
    dailyLossKwh: dto.daily_loss_kwh,
    tariffPkrPerKwh: dto.tariff_pkr_per_kwh,
    washCostPkr: dto.wash_cost_pkr,
  };
}

interface HistoryCoverage {
  recorded_through: string | null;
  logged_through: string | null;
}

/**
 * The newer of the station's recorded data and the site's own log; "logged" when the log is the newer.
 * `fallback` (the history's own last day) covers an answer that names neither.
 */
export function toFreshness(dto: HistoryCoverage, fallback: string): Freshness {
  const { recorded_through: recorded, logged_through: logged } = dto;
  if (logged !== null && (recorded === null || logged >= recorded)) {
    return { through: logged, kind: 'logged' };
  }
  return { through: recorded ?? fallback, kind: 'recorded' };
}

/**
 * Energy history as a screen result: "collecting" until the site has both a full day and a month of
 * figures, otherwise the data `build` makes from the rows and the day the latest month runs to.
 */
export function energyResult<T>(
  dto: EnergyHistoryDto,
  build: (daily: DailyEnergy[], meters: MonthlyMeter[], meteredThrough: string) => T,
): HistoryResult<T> {
  const meteredThrough = dto.metered_through;
  if (dto.daily.length === 0 || dto.monthly.length === 0 || meteredThrough === null) {
    return { status: 'collecting', loggedDays: dto.logged_days };
  }
  return {
    status: 'ready',
    data: build(toDailyEnergy(dto), toMonthlyMeters(dto), meteredThrough),
    freshness: toFreshness(dto, meteredThrough),
  };
}

// Savings and Reports both read the energy history; cache() fetches it once per page render.
export const fetchEnergyHistory = cache(() => apiGet<EnergyHistoryDto>('/api/insights/energy'));
export const fetchOutageHistory = cache(() => apiGet<OutageHistoryDto>('/api/insights/outages'));
export const fetchSoilingHistory = cache(() => apiGet<SoilingHistoryDto>('/api/insights/soiling'));
export const fetchRainForecast = cache(() => apiGet<RainForecastDto>('/api/insights/rain'));

/**
 * The latest full day in the hourly dataset. The plan and the daily brief replay this day, because the
 * recorded data ends before today.
 */
export const fetchLatestDataDay = cache(
  async () => (await apiFetch<DateBoundsDto>('/api/dates', { auth: false })).max_date,
);
