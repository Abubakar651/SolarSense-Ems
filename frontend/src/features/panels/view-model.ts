import { longDate } from '@/lib/dates';
import { fmt } from '@/lib/format';
import { todayInKarachi } from '@/lib/freshness';
import type { DustCollecting, SoilingData } from '@/types/domain/panels';

/** The sample site's default wash price (PKR), reused as the placeholder while a site has no model yet. */
const DEFAULT_WASH_COST_PKR = 1500;

export interface WashAdvice {
  /** Days the dust loss is added up for: until the next rain, at most the look-ahead window. */
  days: number;
  /** True when rain inside the window will clean the panels for free. */
  rainSoon: boolean;
  /** True when the rain forecast could not be fetched, so rain may still come before `days`. */
  rainUnknown: boolean;
  /** Dust cost over those days, in PKR. */
  lossPkr: number;
  /** "2.207 kWh × PKR 34.53 × 6 days = PKR 457" */
  formula: string;
  /** Positive when cleaning pays for itself. */
  netPkr: number;
  wash: boolean;
}

/** Parses what the user typed in the cost field; anything unusable counts as 0. */
export function parseCost(input: string): number {
  return Math.max(0, Number(input.replace(/[^\d.]/g, '')) || 0);
}

export function washAdvice(soiling: SoilingData, costPkr: number): WashAdvice {
  const { dailyLossKwh, tariffPkrPerKwh, horizonDays, daysUntilRain } = soiling;
  const days = Math.min(daysUntilRain ?? horizonDays, horizonDays);
  const lossPkr = dailyLossKwh * tariffPkrPerKwh * days;
  const netPkr = lossPkr - costPkr;

  return {
    days,
    rainSoon: daysUntilRain !== null && daysUntilRain < horizonDays,
    rainUnknown: !soiling.rainForecastAvailable,
    lossPkr,
    formula: `${dailyLossKwh} kWh × PKR ${tariffPkrPerKwh} × ${days} days = PKR ${fmt(lossPkr)}`,
    netPkr,
    wash: netPkr > 0,
  };
}

/** The forecast line starts from today's loss so it joins the history line. */
export function forecastSeries(soiling: SoilingData): (number | null)[] {
  const today = soiling.history.length - 1;
  return [...Array<null>(today).fill(null), soiling.history[today] as number, ...soiling.forecast];
}

/** Money lost to dust per day at the latest soiling level. */
export function dailyLossPkr(soiling: SoilingData): number {
  return soiling.dailyLossKwh * soiling.tariffPkrPerKwh;
}

/** Days of dust loss it takes for one cleaning to pay for itself; null while dust costs nothing. */
export function paybackDays(soiling: SoilingData, costPkr: number): number | null {
  const perDay = dailyLossPkr(soiling);
  return perDay > 0 ? Math.ceil(costPkr / perDay) : null;
}

/** "Last washed Sep 23, 2026", or "Rain cleaned them Nov 10, 2026" when washing rain was the last clean. */
export function lastCleanedLabel(soiling: SoilingData): string {
  return soiling.cleanEvent === 'rain'
    ? `Rain cleaned them ${soiling.lastWashed}`
    : `Last washed ${soiling.lastWashed}`;
}

/** Output loss from which the panels count as dusty. */
const DUSTY_FROM_PCT = 10;

/** Output lost to dust on the latest recorded day (percent). */
export function lossPercent(soiling: SoilingData): number {
  return soiling.history[soiling.history.length - 1] as number;
}

export function isDusty(soiling: SoilingData): boolean {
  return lossPercent(soiling) >= DUSTY_FROM_PCT;
}

/** True when the wash the model is waiting on was recorded today (`today` is YYYY-MM-DD in Asia/Karachi). */
export function washedToday(collecting: DustCollecting, today: string): boolean {
  return collecting.clean?.event === 'wash' && collecting.clean.date === today;
}

/** A same-shaped soiling model of all zeros, for the Panels screen while the site has none yet. */
export function zeroSoilingData(): SoilingData {
  const today = longDate(todayInKarachi(new Date()));
  return {
    history: Array.from({ length: 5 }, () => 0),
    forecast: Array.from({ length: 4 }, () => 0),
    asOf: today,
    lastWashed: today,
    cleanEvent: 'wash',
    defaultWashCostPkr: DEFAULT_WASH_COST_PKR,
    dailyLossKwh: 0,
    tariffPkrPerKwh: 0,
    horizonDays: 14,
    daysUntilRain: null,
    rainForecastAvailable: true,
  };
}

/** What the Panels screen says while the dust model gathers days after the last clean. */
export function collectingMessage({ clean, loggedDays, daysNeeded }: DustCollecting): string {
  if (clean === null) {
    return (
      'No wash is on record and no rain has washed your panels recently. After your next wash, tap ' +
      `"I washed the panels today". The dust estimate starts ${daysNeeded} full days of inverter readings later.`
    );
  }
  const cleaned = clean.event === 'rain' ? 'Rain cleaned your panels' : 'Your panels were washed';
  const days = (n: number) => `${n} full ${n === 1 ? 'day' : 'days'}`;
  return (
    `${cleaned} on ${longDate(clean.date)}. The dust estimate needs ${days(daysNeeded)} of inverter ` +
    `readings after that; ${loggedDays} so far.`
  );
}
