import type { SavingsData, SavingsSeries } from '@/types/domain/savings';
import { MONTHLY_METER, TELEMETRY_DAY, type MonthlyMeter } from '../../mock/lhr-res-01';
import { DAILY_ENERGY, type DailyEnergy } from '../../mock/lhr-res-01-history';
import { SAMPLE_RATES, valueOfEnergy, type EnergyRates } from '../../mock/valuation';
import type { SavingsRepository } from './savings.repository';

const MONTH_NAMES = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const WEEK_DAYS = 7;
const MONTH_DAYS = 30;

const DAY_MS = 86_400_000;

/**
 * The last `days` calendar days through the latest daily row: logged days can have gaps between them,
 * so the last N rows could span far more than N days.
 */
function dailySeries(
  daily: readonly DailyEnergy[],
  days: number,
  rates: EnergyRates,
): SavingsSeries {
  const latest = daily[daily.length - 1]?.[0];
  const cutoff = latest
    ? new Date(Date.parse(`${latest}T00:00:00Z`) - days * DAY_MS).toISOString().slice(0, 10)
    : '';
  const rows = daily
    .filter(([date]) => date > cutoff)
    .map(([date, , load, imported, exported]) => ({
      date,
      ...valueOfEnergy(load, imported, exported, rates),
    }));
  return {
    labels: rows.map(({ date }) =>
      days === WEEK_DAYS
        ? (WEEKDAYS[new Date(`${date}T00:00:00Z`).getUTCDay()] as string)
        : String(Number(date.slice(8))),
    ),
    values: rows.map(({ totalPkr }) => totalPkr),
    exportPkr: rows.map(({ exportPkr }) => exportPkr),
    title: 'Daily savings',
    word: 'day',
  };
}

function monthlySeries(meters: readonly MonthlyMeter[], rates: EnergyRates): SavingsSeries {
  const rows = meters.map((m) => valueOfEnergy(m.loadKwh, m.purchasedKwh, m.soldKwh, rates));
  return {
    labels: meters.map(({ month }) => MONTH_NAMES[Number(month.slice(5)) - 1] as string),
    values: rows.map(({ totalPkr }) => totalPkr),
    exportPkr: rows.map(({ exportPkr }) => exportPkr),
    title: 'Monthly savings',
    word: 'month',
  };
}

function currentMonth(
  meters: readonly MonthlyMeter[],
  meteredThrough: string,
  rates: EnergyRates,
): SavingsData['currentMonth'] {
  const latest = meters[meters.length - 1] as MonthlyMeter;
  const { loadKwh, purchasedKwh, soldKwh } = latest;
  const lastDay = latest.lastDay ?? Number(meteredThrough.slice(8));
  return {
    label: `${MONTH_NAMES[Number(meteredThrough.slice(5, 7)) - 1]} ${latest.firstDay ?? 1}–${lastDay}`,
    costPkr: Math.round(
      purchasedKwh * rates.selfConsumedPkrPerKwh - soldKwh * rates.exportPkrPerKwh,
    ),
    withoutSolarPkr: Math.round(loadKwh * rates.selfConsumedPkrPerKwh),
    selfPoweredPct: Math.round(((loadKwh - purchasedKwh) / loadKwh) * 100),
  };
}

/**
 * The Savings screen from recorded daily energy (oldest first) and monthly meter balances. Shared by the
 * sample data and the API repository. `meteredThrough` is the last day the latest month covers; `rates`
 * are the sample site's for sample data and the backend tariff engine's for the user's own tariff live.
 */
export function buildSavings(
  daily: readonly DailyEnergy[],
  meters: readonly MonthlyMeter[],
  meteredThrough: string,
  rates: EnergyRates,
): SavingsData {
  return {
    week: dailySeries(daily, WEEK_DAYS, rates),
    month: dailySeries(daily, MONTH_DAYS, rates),
    year: monthlySeries(meters, rates),
    currentMonth: currentMonth(meters, meteredThrough, rates),
    exportRatePkr: rates.exportPkrPerKwh,
  };
}

export const savingsMock: SavingsRepository = {
  async getSavings() {
    return {
      status: 'ready',
      data: buildSavings(DAILY_ENERGY, MONTHLY_METER, TELEMETRY_DAY, SAMPLE_RATES),
      freshness: { through: TELEMETRY_DAY, kind: 'sample' },
    };
  },
};
