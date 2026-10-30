import { fmt } from '@/lib/format';
import type { SoilingData } from '@/types/domain/panels';

export interface WashAdvice {
  /** Days the dust loss is added up for: until the next rain, at most the look-ahead window. */
  days: number;
  /** True when rain inside the window will clean the panels for free. */
  rainSoon: boolean;
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

/** Days of dust loss it takes for one cleaning to pay for itself. */
export function paybackDays(soiling: SoilingData, costPkr: number): number {
  return Math.ceil(costPkr / dailyLossPkr(soiling));
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
