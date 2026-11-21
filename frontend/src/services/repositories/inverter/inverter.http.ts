import type { InverterReading, Reading } from '@/types/domain/inverter';
import { ApiError, apiGet } from '../../http/client';
import type { InverterLiveDto } from '../../http/dto';
import type { InverterRepository } from './inverter.repository';

const OFFLINE_MESSAGE =
  'SolarSense can’t reach your inverter right now. It may be offline, or not on the same network as the server.';
const NOT_CONFIGURED_MESSAGE =
  'No inverter is connected yet. Add your inverter’s IP address in Settings, under Site & hardware.';

/** The live reader sends 0 for a sensor it could not read; for these values 0 is never a real reading. */
const sensor = (value: number): Reading => (value === 0 ? null : value);

export function toInverterReading(dto: InverterLiveDto): InverterReading {
  return {
    status: 'online',
    isSample: false,
    data: {
      timestamp: dto.timestamp_iso,
      modelName: dto.model_name,
      serialNumber: dto.serial_number,
      batterySocPct: dto.battery_soc_pct,
      batterySohPct: sensor(dto.battery_soh_pct),
      batteryVoltageV: sensor(dto.battery_voltage_v),
      batteryCurrentA: dto.battery_current_a,
      batteryPowerW: dto.battery_power_w,
      batteryMode: dto.battery_mode,
      batteryTempC: sensor(dto.battery_temp_c),
      totalPvPowerW: dto.total_pv_power_w,
      pv1PowerW: dto.pv1_power_w,
      pv2PowerW: dto.pv2_power_w,
      houseConsumptionW: dto.house_consumption_w,
      gridVoltageV: sensor(dto.grid_voltage_v),
      gridFrequencyHz: sensor(dto.grid_frequency_hz),
      gridActivePowerW: dto.grid_active_power_w,
      gridMode: dto.grid_mode,
      isGridConnected: dto.is_grid_connected,
      isBlackout: dto.is_blackout,
      backupVoltageV: sensor(dto.backup_voltage_v),
      backupPowerW: dto.backup_power_w,
      workMode: dto.work_mode,
      todayPvKwh: dto.today_pv_kwh,
      todayExportKwh: dto.today_export_kwh,
      todayImportKwh: dto.today_import_kwh,
      todayLoadKwh: dto.today_load_kwh,
      todayBatteryChargeKwh: dto.today_battery_charge_kwh,
      todayBatteryDischargeKwh: dto.today_battery_discharge_kwh,
      inverterTempAirC: sensor(dto.inverter_temp_air_c),
      inverterTempRadiatorC: sensor(dto.inverter_temp_radiator_c),
    },
  };
}

export const inverterHttp: InverterRepository = {
  async getLive() {
    try {
      return toInverterReading(await apiGet<InverterLiveDto>('/api/v2/inverter/live', '/inverter'));
    } catch (error) {
      // 503: the API could not reach the inverter, or this server could not reach the API.
      if (error instanceof ApiError && error.status === 503) {
        return { status: 'offline', message: OFFLINE_MESSAGE };
      }
      if (
        error instanceof ApiError &&
        error.status === 404 &&
        error.code === 'inverter_not_configured'
      ) {
        return { status: 'offline', message: NOT_CONFIGURED_MESSAGE };
      }
      throw error;
    }
  },
};
