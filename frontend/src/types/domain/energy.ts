/** A local time of day on the sample day. */
export interface ClockTime {
  hour: number;
  minute: number;
}

/** One day of hourly energy flows, in UI terms (kW unless noted). */
export interface DayPlan {
  /** True while the numbers are replayed from recorded data; drives the "Sample data" labels. */
  isSample: boolean;
  /** Calendar day the hourly values were recorded on (YYYY-MM-DD). */
  sampleDate: string;
  /** Tariff rates in PKR per kWh; peak applies between peakStartHour and peakEndHour. */
  tariff: { peakPkr: number; offPeakPkr: number; exportPkr: number };
  solar: number[];
  /** Home usage. */
  load: number[];
  /** Battery level at the end of each hour (percent). */
  soc: number[];
  /** Grid import. */
  grid: number[];
  /** Battery charge power. */
  charge: number[];
  peakStartHour: number;
  peakEndHour: number;
  batteryCapacityKwh: number;
  reserveFloorKwh: number;
  /** Local time the sample clock starts at. */
  clockStart: ClockTime;
}
