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
  /**
   * Tariff rates in PKR per kWh; peak applies between peakStartHour and peakEndHour. Live: the all-in rates
   * the backend's tariff engine priced the plan at (equal on a flat slab tariff).
   */
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
  /** Local time the clock starts at: the real time in Lahore for a live plan. */
  clockStart: ClockTime;
  /**
   * How today's forecast was made; null while a recorded day is replayed. The forecasters need
   * `historyHours` of recent history; the hours the inverter log doesn't cover yet come from the
   * recorded dataset, which makes the forecast less accurate.
   */
  forecast: { loggedHistoryHours: number; historyHours: number } | null;
  /** True when no battery level was logged near midnight, so the starting level (and the curve) is assumed. */
  initialSocAssumed: boolean;
}

/**
 * Today's plan, or why there is none yet: the site's inverter log has none of the recent history the
 * forecast needs (collecting), or the weather forecast can't be fetched (unavailable).
 */
export type DayPlanResult =
  | { status: 'ready'; plan: DayPlan }
  | { status: 'collecting' }
  | { status: 'unavailable' };

/** One day of metered energy, all in kWh. */
export interface DailyEnergyDay {
  /** YYYY-MM-DD */
  date: string;
  solarKwh: number;
  loadKwh: number;
  importKwh: number;
  exportKwh: number;
  /** Null on days the battery was not measured. */
  batteryChargedKwh?: number | null;
  batteryDischargedKwh?: number | null;
}

/** One calendar month of metered energy, all in kWh. */
export interface MonthEnergy {
  /** YYYY-MM */
  month: string;
  solarKwh: number;
  loadKwh: number;
  importKwh: number;
  exportKwh: number;
}

/** Everything the Energy screen's history charts read: daily rows, and monthly rows up to 24 months back. */
export interface EnergyHistory {
  days: DailyEnergyDay[];
  months: MonthEnergy[];
}

/** One point of a day's power curve (kW). Battery is + while charging, grid is + while exporting. */
export interface CurvePoint {
  /** Local HH:MM */
  time: string;
  pvKw: number;
  loadKw: number;
  /** Null where the source did not measure it. */
  batteryKw: number | null;
  gridKw: number | null;
  socPct: number | null;
}

/** The day's highest readings, each null when the day never measured it. */
export interface DayPeaks {
  pvKw: number | null;
  loadKw: number | null;
  chargeKw: number | null;
  dischargeKw: number | null;
  importKw: number | null;
  exportKw: number | null;
}

export interface DayCurve {
  date: string;
  /** Minutes between points: 5 for logged and recorded 5-minute data, 60 for hourly records. */
  intervalMinutes: number;
  points: CurvePoint[];
  peaks: DayPeaks;
  /** Every day with a curve, oldest first. */
  dates: string[];
}
