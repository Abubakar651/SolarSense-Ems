export interface SoilingData {
  /** Output lost to dust (percent) on each day since the last wash, up to the latest recorded day. */
  history: number[];
  /** Projected loss for the days after that day (percent), without cleaning. */
  forecast: number[];
  /** Day the numbers are as of, e.g. "Oct 7, 2026". */
  asOf: string;
  /** Day of the last wash, e.g. "Sep 23, 2026". */
  lastWashed: string;
  defaultWashCostPkr: number;
  /** Energy lost per day at the latest soiling level (kWh). */
  dailyLossKwh: number;
  tariffPkrPerKwh: number;
  /** Longest look-ahead (days) the wash calculator adds up the dust loss for. */
  horizonDays: number;
  /** Days until the next rain of 3 mm or more, which washes the panels for free; null when none is forecast. */
  daysUntilRain: number | null;
}
