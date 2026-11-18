import type { InverterReading } from '@/types/domain/inverter';
import { LAST_TELEMETRY_ROW, STATION, TELEMETRY_DAY_KWH } from '../../mock/lhr-res-01';
import type { InverterRepository } from './inverter.repository';

const W_PER_KW = 1000;
const BATTERY_NOMINAL_V = 51.2;

/**
 * The last recorded reading (see LAST_TELEMETRY_ROW), converted to the live endpoint's units and signs:
 * battery power positive = charging, grid power positive = exporting. Anything the recording does not
 * hold (SoH, temperatures, grid voltage and frequency, backup bus) is null and shows as "—".
 * Daily totals are those of the recorded day, not of the reading's own date.
 */
function sampleReading(): InverterReading {
  const row = LAST_TELEMETRY_ROW;
  // The recording counts discharge as positive. `0 -` rather than a minus sign keeps zero from becoming -0.
  const batteryPowerW = 0 - row.batteryKw * W_PER_KW;
  return {
    status: 'online',
    isSample: true,
    data: {
      timestamp: row.timestamp,
      modelName: 'GoodWe ES-Uniq hybrid',
      serialNumber: STATION.serial,
      batterySocPct: row.batterySocPct,
      batterySohPct: null,
      batteryVoltageV: BATTERY_NOMINAL_V,
      batteryCurrentA: batteryPowerW / BATTERY_NOMINAL_V,
      batteryPowerW,
      batteryMode: batteryPowerW === 0 ? 'Standby' : batteryPowerW > 0 ? 'Charge' : 'Discharge',
      batteryTempC: null,
      totalPvPowerW: row.pvKw * W_PER_KW,
      pv1PowerW: row.pvKw * W_PER_KW,
      pv2PowerW: 0,
      houseConsumptionW: row.loadKw * W_PER_KW,
      gridVoltageV: null,
      gridFrequencyHz: null,
      gridActivePowerW: row.gridKw * W_PER_KW,
      gridMode: 'Connected',
      isGridConnected: true,
      isBlackout: false,
      backupVoltageV: null,
      backupPowerW: null,
      workMode: 'Normal (On-Grid)',
      todayPvKwh: TELEMETRY_DAY_KWH.pv,
      todayExportKwh: TELEMETRY_DAY_KWH.exported,
      todayImportKwh: TELEMETRY_DAY_KWH.imported,
      todayLoadKwh: TELEMETRY_DAY_KWH.load,
      todayBatteryChargeKwh: TELEMETRY_DAY_KWH.batteryCharged,
      todayBatteryDischargeKwh: TELEMETRY_DAY_KWH.batteryDischarged,
      inverterTempAirC: null,
      inverterTempRadiatorC: null,
    },
  };
}

export const inverterMock: InverterRepository = {
  async getLive() {
    return sampleReading();
  },
};
