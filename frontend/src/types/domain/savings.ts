export type SavingsRange = 'week' | 'month' | 'year';

export interface SavingsSeries {
  labels: string[];
  /** PKR saved per period. */
  values: number[];
  /** The part of each value that is export credit (PKR). */
  exportPkr: number[];
  /** Title of the chart card, e.g. "Daily savings". */
  title: string;
  /** The period unit, singular ("day" / "month"). */
  word: string;
}

/** The latest month so far, with and without the solar system. */
export interface CurrentMonth {
  /** e.g. "Oct 1-26" */
  label: string;
  /** Energy cost with solar: grid purchases minus export credit (PKR, can be negative). */
  costPkr: number;
  /** Energy cost if all usage had been bought from the grid (PKR). */
  withoutSolarPkr: number;
  /** Share of usage not bought from the grid (percent). */
  selfPoweredPct: number;
}

export type SavingsData = Record<SavingsRange, SavingsSeries> & {
  currentMonth: CurrentMonth;
  /** Export credit paid per kWh sent to the grid (PKR). */
  exportRatePkr: number;
};
