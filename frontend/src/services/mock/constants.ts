import { HOURLY_LOAD_KW, STATION, TARIFF } from './lhr-res-01';

/** Site used by every mock repository: Station LHR-RES-01, from the backend's data (see ./lhr-res-01.ts). */
export const SAMPLE_SITE = {
  /** Battery capacity (kWh) and the share held back for outages. */
  batteryCapacityKwh: STATION.batteryKwh,
  reserveFloorKwh: STATION.reserveFloorKwh,
  maxChargeKw: STATION.maxChargeKw,
  maxDischargeKw: STATION.maxDischargeKw,
  /** Round-trip efficiency applied on each leg. */
  efficiency: STATION.efficiency,
  /** Evening peak tariff window [start, end) in local hours. */
  peakStartHour: TARIFF.peakStartHour,
  peakEndHour: TARIFF.peakEndHour,
  /** The sample clock starts here (local time). */
  clockStart: { hour: 15, minute: 42 },
} as const;

/** Hourly home usage in kW for the sample day. */
export const SAMPLE_LOAD_KW = HOURLY_LOAD_KW;
