import type { DayPlan } from '@/types/domain/energy';
import { SAMPLE_SITE } from '../../mock/constants';
import { TARIFF, TELEMETRY_DAY } from '../../mock/lhr-res-01';
import { simulateDay } from '../../mock/engine/day-simulation';
import type { EnergyRepository } from './energy.repository';

export const energyMock: EnergyRepository = {
  async getDayPlan(): Promise<DayPlan> {
    const day = simulateDay();
    return {
      isSample: true,
      sampleDate: TELEMETRY_DAY,
      tariff: {
        peakPkr: TARIFF.peakPkrPerKwh,
        offPeakPkr: TARIFF.offPeakPkrPerKwh,
        exportPkr: TARIFF.exportPkrPerKwh,
      },
      ...day,
      peakStartHour: SAMPLE_SITE.peakStartHour,
      peakEndHour: SAMPLE_SITE.peakEndHour,
      batteryCapacityKwh: SAMPLE_SITE.batteryCapacityKwh,
      reserveFloorKwh: SAMPLE_SITE.reserveFloorKwh,
      clockStart: { ...SAMPLE_SITE.clockStart },
    };
  },
};
