export interface WeeklyRow {
  week: string;
  solarKwh: string;
  gridKwh: string;
  savedPkr: string;
}

export interface MonthReport {
  /** e.g. "October 2026" */
  name: string;
  /** Days the meter figures cover, e.g. "Metered Oct 1-26". */
  coverage: string;
  /** Headline figures of the monthly report. */
  totals: { label: string; value: string }[];
  /** PKR saved on each day with recorded data, and the day of the month each value belongs to. */
  dailyLabels: string[];
  dailyValues: number[];
  weeks: WeeklyRow[];
}

export interface ReportData {
  /** Station the report is about, e.g. "LHR-RES-01 · Johar Town". */
  site: string;
  /** Months the report can be generated for, newest first. */
  months: MonthReport[];
}
