import { fmt } from '@/lib/format';
import type { MonthReport, ReportData, WeeklyRow } from '@/types/domain/reports';
import { MONTHLY_METER, STATION, TELEMETRY_DAY, type MonthlyMeter } from '../../mock/lhr-res-01';
import { DAILY_ENERGY, type DailyEnergy } from '../../mock/lhr-res-01-history';
import { SAMPLE_RATES, valueOfEnergy, type EnergyRates } from '../../mock/valuation';
import type { ReportsRepository } from './reports.repository';

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
const REPORT_MONTHS = 3;
const WEEK_LENGTH = 7;

const sum = (values: number[]) => values.reduce((a, b) => a + b, 0);
const daysInMonth = (month: string) =>
  new Date(Date.UTC(Number(month.slice(0, 4)), Number(month.slice(5)), 0)).getUTCDate();

/** Days 1-7, 8-14, 15-21 and the rest of the month, for the days that have hourly data. */
function weeklyRows(
  month: string,
  days: DailyEnergy[],
  short: string,
  rates: EnergyRates,
): WeeklyRow[] {
  const rows: WeeklyRow[] = [];
  for (let first = 1; first <= daysInMonth(month); first += WEEK_LENGTH) {
    const last = first + WEEK_LENGTH - 1 > 21 ? daysInMonth(month) : first + WEEK_LENGTH - 1;
    const week = days.filter(
      ([date]) => Number(date.slice(8)) >= first && Number(date.slice(8)) <= last,
    );
    if (week.length === 0) continue;
    rows.push({
      week: `${short} ${first}–${Number(week[week.length - 1]?.[0].slice(8))}`,
      solarKwh: fmt(sum(week.map(([, solar]) => solar))),
      gridKwh: fmt(sum(week.map(([, , , imported]) => imported))),
      savedPkr: fmt(
        sum(
          week.map(
            ([, , load, imported, exported]) =>
              valueOfEnergy(load, imported, exported, rates).totalPkr,
          ),
        ),
      ),
    });
    if (last === daysInMonth(month)) break;
  }
  return rows;
}

function monthReport(
  meter: MonthlyMeter,
  daily: readonly DailyEnergy[],
  meteredThrough: string,
  rates: EnergyRates,
): MonthReport {
  const month = meter.month;
  const name = MONTH_NAMES[Number(month.slice(5)) - 1] as string;
  const short = name.slice(0, 3);
  const days = daily.filter(([date]) => date.startsWith(month));
  const firstDay = meter.firstDay ?? 1;
  const lastDay =
    meter.lastDay ??
    (month === meteredThrough.slice(0, 7) ? Number(meteredThrough.slice(8)) : daysInMonth(month));
  const saved = valueOfEnergy(meter.loadKwh, meter.purchasedKwh, meter.soldKwh, rates);

  return {
    name: `${name} ${month.slice(0, 4)}`,
    coverage: `Metered ${short} ${firstDay}–${lastDay}`,
    totals: [
      { label: 'Solar generated', value: `${fmt(meter.pvKwh)} kWh` },
      { label: 'Grid imported', value: `${fmt(meter.purchasedKwh)} kWh` },
      { label: 'Exported', value: `${fmt(meter.soldKwh)} kWh` },
      { label: 'Total saved', value: `PKR ${fmt(saved.totalPkr)}` },
    ],
    dailyLabels: days.map(([date]) => String(Number(date.slice(8)))),
    dailyValues: days.map(
      ([, , load, imported, exported]) => valueOfEnergy(load, imported, exported, rates).totalPkr,
    ),
    weeks: weeklyRows(month, days as DailyEnergy[], short, rates),
  };
}

/**
 * The Reports screen: the latest three metered months, newest first. Shared by the sample data and the
 * API repository. \`meteredThrough\` is the last day the latest month's meter figures cover.
 */
export function buildReport(
  site: string,
  meters: readonly MonthlyMeter[],
  daily: readonly DailyEnergy[],
  meteredThrough: string,
  rates: EnergyRates,
): ReportData {
  return {
    site,
    months: meters
      .slice(-REPORT_MONTHS)
      .reverse()
      .map((meter) => monthReport(meter, daily, meteredThrough, rates)),
  };
}

export const reportsMock: ReportsRepository = {
  async getReport() {
    return {
      status: 'ready',
      data: {
        ...buildReport(
          `${STATION.id} · ${STATION.area}`,
          MONTHLY_METER,
          DAILY_ENERGY,
          TELEMETRY_DAY,
          SAMPLE_RATES,
        ),
        // The sample's daily rows end on their last recorded day.
        hourlyThrough: DAILY_ENERGY[DAILY_ENERGY.length - 1]?.[0] ?? null,
      },
      freshness: { through: TELEMETRY_DAY, kind: 'sample' },
    };
  },
  async getEmailPrefs() {
    return { monthly: true, weekly: false, sendTo: 'zaeem@example.com' };
  },
};
