/**
 * Recorded data from Station LHR-RES-01 (GoodWe hybrid inverter, Johar Town, Lahore), copied from the
 * Python backend's datasets so the mock repositories show real figures, not placeholders.
 * The source file is named above each block. Values are rounded only.
 */

/** README.md, AGENTS.md, docs/SEMS_PORTAL_AI_AGENT_EXTRACTED_DATA.md, src/data_engineering/feature_store.py */
export const STATION = {
  id: 'LHR-RES-01',
  city: 'Lahore',
  area: 'Johar Town',
  inverter: 'GoodWe',
  serial: '9010KESC253L0146',
  /** 12 bifacial panels of 585 W. */
  solarKwp: 7.02,
  batteryKwh: 5.12,
  /** Battery emergency reserve floor: 15% of 5.12 kWh. */
  reserveFloorKwh: 0.768,
  maxChargeKw: 5,
  maxDischargeKw: 5,
  /** Applied on each leg (charge and discharge). */
  efficiency: 0.95,
} as const;

/** src/lesco-tarrif.json: LESCO A-1 time-of-use with net metering. */
export const TARIFF = {
  peakPkrPerKwh: 46.85,
  offPeakPkrPerKwh: 34.53,
  exportPkrPerKwh: 27,
  peakStartHour: 18,
  peakEndHour: 22,
  washCostPkr: 1500,
} as const;

/** data/processed/solar_timeseries/goodwe_station_5min_telemetry.csv: the one fully measured day. */
export const TELEMETRY_DAY = '2026-10-26';

/** Timestamp of the last inverter reading in that file. */
export const LAST_READING = '2026-10-27 02:10';

/** Hourly mean PV output (kW) on TELEMETRY_DAY. */
export const HOURLY_SOLAR_KW: readonly number[] = [
  0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.09, 0.94, 2.08, 3.16, 3.7, 4.27, 3.76, 3.26, 2.44, 1.52, 0.37,
  0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
];

/** Hourly mean home usage (kW) on TELEMETRY_DAY. */
export const HOURLY_LOAD_KW: readonly number[] = [
  0.6, 0.74, 0.81, 0.72, 0.68, 0.69, 0.65, 0.64, 0.86, 0.85, 1.1, 1.6, 1.21, 1.22, 1.14, 0.8, 0.71,
  0.73, 1.18, 1.18, 0.95, 0.99, 0.79, 1.03,
];

export interface MonthlyMeter {
  month: string;
  pvKwh: number;
  loadKwh: number;
  purchasedKwh: number;
  soldKwh: number;
}

/**
 * data/processed/residential_load/lahore_residential_monthly_metered_ground_truth.csv (SEMS portal station balance).
 * 2026-10 covers 1 to 26 October only.
 */
export const MONTHLY_METER: readonly MonthlyMeter[] = [
  { month: '2025-11', pvKwh: 416.5, loadKwh: 290.9, purchasedKwh: 154.1, soldKwh: 234.8 },
  { month: '2025-12', pvKwh: 351.8, loadKwh: 438.1, purchasedKwh: 281.7, soldKwh: 141.8 },
  { month: '2026-01', pvKwh: 382.4, loadKwh: 513.3, purchasedKwh: 393.5, soldKwh: 211.7 },
  { month: '2026-02', pvKwh: 575.8, loadKwh: 261.4, purchasedKwh: 142.5, soldKwh: 403 },
  { month: '2026-03', pvKwh: 781.3, loadKwh: 494.3, purchasedKwh: 272.4, soldKwh: 484 },
  { month: '2026-04', pvKwh: 1018, loadKwh: 661.5, purchasedKwh: 362.4, soldKwh: 626.6 },
  { month: '2026-05', pvKwh: 1170.6, loadKwh: 903, purchasedKwh: 510, soldKwh: 689.7 },
  { month: '2026-06', pvKwh: 1183.9, loadKwh: 1371.4, purchasedKwh: 769.8, soldKwh: 492.6 },
  { month: '2026-07', pvKwh: 813.2, loadKwh: 1843.9, purchasedKwh: 1255.5, soldKwh: 143.2 },
  { month: '2026-08', pvKwh: 715.9, loadKwh: 1763.5, purchasedKwh: 1195.5, soldKwh: 65.7 },
  { month: '2026-09', pvKwh: 819.5, loadKwh: 1494.4, purchasedKwh: 1017.2, soldKwh: 254.4 },
  { month: '2026-10', pvKwh: 579.5, loadKwh: 973.6, purchasedKwh: 672.7, soldKwh: 214.4 },
];

export interface InverterAlarm {
  name: string;
  start: string;
  end: string;
  status: string;
  severity: string;
  minutes: number;
}

/** data/raw/goodwe_inverter_reports/goodwe_sems_agent_alarm_events_oct2026.csv, newest first. */
export const ALARMS: readonly InverterAlarm[] = [
  {
    name: 'Grid Power Outage (Grid Loss)',
    start: '2026-10-26 19:27:56',
    end: '2026-10-26 19:29:02',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 1.1,
  },
  {
    name: 'Grid Line Under-Voltage L2',
    start: '2026-10-26 19:27:56',
    end: '2026-10-26 19:29:02',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 1.1,
  },
  {
    name: 'Grid Under-Frequency L2',
    start: '2026-10-26 19:27:56',
    end: '2026-10-26 19:29:02',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 1.1,
  },
  {
    name: 'Grid Under-Voltage Protection',
    start: '2026-10-26 18:18:56',
    end: '2026-10-26 18:20:03',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 1.12,
  },
  {
    name: 'Grid Over-Frequency Protection',
    start: '2026-10-26 18:18:56',
    end: '2026-10-26 18:20:03',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 1.12,
  },
  {
    name: 'Grid Power Outage (Grid Loss)',
    start: '2026-10-26 18:04:56',
    end: '2026-10-26 18:20:03',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 15.12,
  },
  {
    name: 'Grid Over-Frequency L2',
    start: '2026-10-26 18:04:56',
    end: '2026-10-26 18:19:02',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 14.1,
  },
  {
    name: 'Grid Line Under-Voltage L2',
    start: '2026-10-26 18:04:56',
    end: '2026-10-26 18:19:02',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 14.1,
  },
  {
    name: 'Grid Line Under-Voltage L2',
    start: '2026-10-25 21:48:51',
    end: '2026-10-26 01:14:56',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 206.08,
  },
  {
    name: 'Grid Power Outage (Grid Loss)',
    start: '2026-10-25 21:48:51',
    end: '2026-10-26 01:14:56',
    status: 'Recovered',
    severity: 'Fault',
    minutes: 206.08,
  },
];

/**
 * Soiling model from data/processed/master_ems_timeseries.csv (column soiling_model_pr), anchored at the
 * confirmed wash on 2026-09-23. modelPr[d] is the model's performance ratio d days after the wash; it decays
 * by a constant daily factor, so later days continue the same curve.
 */
export const SOILING = {
  washDate: '2026-09-23',
  /** Last day of the dataset: 14 days after the wash. */
  asOf: '2026-10-07',
  modelPr: [
    1.085689, 1.072619, 1.059706, 1.046949, 1.034345, 1.021893, 1.00959, 0.997436, 0.985428,
    0.973565, 0.961845, 0.950265, 0.938825, 0.927523, 0.916357,
  ],
  /** The backend's soiling_loss_kwh for 2026-10-07. */
  dailyLossKwh: 2.207,
} as const;
