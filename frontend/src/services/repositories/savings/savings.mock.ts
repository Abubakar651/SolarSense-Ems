import type { SavingsData, SavingsSeries } from '@/types/domain/savings';
import { MONTHLY_METER, TARIFF, TELEMETRY_DAY } from '../../mock/lhr-res-01';
import { DAILY_ENERGY } from '../../mock/lhr-res-01-history';
import { valueOfEnergy } from '../../mock/valuation';
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

function dailySeries(days: number): SavingsSeries {
  const rows = DAILY_ENERGY.slice(-days).map(([date, , load, imported, exported]) => ({
    date,
    ...valueOfEnergy(load, imported, exported),
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

function monthlySeries(): SavingsSeries {
  const rows = MONTHLY_METER.map((m) => valueOfEnergy(m.loadKwh, m.purchasedKwh, m.soldKwh));
  return {
    labels: MONTHLY_METER.map(({ month }) => MONTH_NAMES[Number(month.slice(5)) - 1] as string),
    values: rows.map(({ totalPkr }) => totalPkr),
    exportPkr: rows.map(({ exportPkr }) => exportPkr),
    title: 'Monthly savings',
    word: 'month',
  };
}

function currentMonth(): SavingsData['currentMonth'] {
  const latest = MONTHLY_METER[MONTHLY_METER.length - 1] as (typeof MONTHLY_METER)[number];
  const { loadKwh, purchasedKwh, soldKwh } = latest;
  return {
    label: `${MONTH_NAMES[Number(TELEMETRY_DAY.slice(5, 7)) - 1]} 1–${Number(TELEMETRY_DAY.slice(8))}`,
    costPkr: Math.round(purchasedKwh * TARIFF.offPeakPkrPerKwh - soldKwh * TARIFF.exportPkrPerKwh),
    withoutSolarPkr: Math.round(loadKwh * TARIFF.offPeakPkrPerKwh),
    selfPoweredPct: Math.round(((loadKwh - purchasedKwh) / loadKwh) * 100),
  };
}

export const savingsMock: SavingsRepository = {
  async getSavings() {
    return {
      week: dailySeries(WEEK_DAYS),
      month: dailySeries(MONTH_DAYS),
      year: monthlySeries(),
      currentMonth: currentMonth(),
      exportRatePkr: TARIFF.exportPkrPerKwh,
    };
  },
};
