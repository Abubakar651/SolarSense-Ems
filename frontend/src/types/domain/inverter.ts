/** A sensor value the inverter did not report. The backend sends 0 or a default instead, so a mapper may fill these. */
export type Reading = number | null;

/**
 * One live snapshot from the inverter. Fields mirror GET /api/v2/inverter/live (InverterLiveResponse in
 * src/api/schemas.py) in camelCase.
 *
 * Sign conventions, from src/data_engineering/goodwe_live_reader.py:
 *  - batteryPowerW: positive = charging, negative = discharging. The recorded history in
 *    data/processed/solar_timeseries uses the opposite sign (positive = discharging), so convert when mixing the two.
 *  - gridActivePowerW: positive = exporting to the grid, negative = importing.
 */
export interface InverterLive {
  /** ISO 8601 with offset, Asia/Karachi. */
  timestamp: string;
  modelName: string;
  serialNumber: string;
  batterySocPct: number;
  batterySohPct: Reading;
  batteryVoltageV: Reading;
  batteryCurrentA: Reading;
  batteryPowerW: number;
  /** "Charge", "Discharge", "Standby", ... as reported by the inverter. */
  batteryMode: string;
  batteryTempC: Reading;
  totalPvPowerW: number;
  pv1PowerW: number;
  pv2PowerW: number;
  houseConsumptionW: number;
  gridVoltageV: Reading;
  gridFrequencyHz: Reading;
  gridActivePowerW: number;
  gridMode: string;
  isGridConnected: boolean;
  isBlackout: boolean;
  backupVoltageV: Reading;
  backupPowerW: Reading;
  workMode: string;
  todayPvKwh: number;
  todayExportKwh: number;
  todayImportKwh: number;
  todayLoadKwh: number;
  todayBatteryChargeKwh: number;
  todayBatteryDischargeKwh: number;
  inverterTempAirC: Reading;
  inverterTempRadiatorC: Reading;
}

/** The endpoint answers 503 when the inverter cannot be reached. */
export type InverterReading =
  | {
      status: 'online';
      /** True while the figures are a recorded reading, not a live one; drives the "Sample data" label. */
      isSample: boolean;
      data: InverterLive;
    }
  | { status: 'offline'; message: string };
