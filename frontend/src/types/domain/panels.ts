import type { HistoryResult } from './history';

export interface SoilingData {
  /** Output lost to dust (percent) on each day since the last wash, up to the latest recorded day. */
  history: number[];
  /** Projected loss for the days after that day (percent), without cleaning. */
  forecast: number[];
  /** Day the numbers are as of, e.g. "Oct 7, 2026". */
  asOf: string;
  /** Day the panels were last cleaned, e.g. "Sep 23, 2026": a wash, or rain heavy enough to wash them. */
  lastWashed: string;
  cleanEvent: CleanEvent;
  defaultWashCostPkr: number;
  /** Energy lost per day at the latest soiling level (kWh). */
  dailyLossKwh: number;
  /** What one kWh lost to dust costs at the site's tariff. */
  tariffPkrPerKwh: number;
  /** Longest look-ahead (days) the wash calculator adds up the dust loss for. */
  horizonDays: number;
  /**
   * Days until the next rain of 3 mm or more, which washes the panels for free; null when none is
   * forecast, or when the forecast could not be fetched (rainForecastAvailable false).
   */
  daysUntilRain: number | null;
  rainForecastAvailable: boolean;
}

export type CleanEvent = 'wash' | 'rain';

/**
 * The dust model is still gathering days: it needs `daysNeeded` complete logged days after the panels were
 * last cleaned. `clean` is null when no wash was recorded and no washing rain fell recently.
 */
export interface DustCollecting {
  status: 'collecting';
  loggedDays: number;
  daysNeeded: number;
  /** `date` is YYYY-MM-DD (Asia/Karachi). */
  clean: { event: CleanEvent; date: string } | null;
}

/** What the Panels screen gets: the dust model, how far it is from having one, or "unavailable". */
export type SoilingResult =
  Exclude<HistoryResult<SoilingData>, { status: 'collecting' }> | DustCollecting;
