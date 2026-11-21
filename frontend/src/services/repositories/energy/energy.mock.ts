import type { DayPlan } from '@/types/domain/energy';
import { SAMPLE_SITE } from '../../mock/constants';
import { TARIFF, TELEMETRY_DAY } from '../../mock/lhr-res-01';
import { DAILY_ENERGY } from '../../mock/lhr-res-01-history';
import { simulateDay } from '../../mock/engine/day-simulation';
import { curveFromPlan } from './day-curve';
import { sampleEnergyHistory } from './energy-history';
import type { EnergyRepository } from './energy.repository';

/** The bundled sample day on the sample site's battery and tariff. */
function samplePlan(): DayPlan {
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
    forecast: null,
    initialSocAssumed: false,
  };
}

export const energyMock: EnergyRepository = {
  async getDayPlan() {
    return { status: 'ready', plan: samplePlan() };
  },
  async getEnergyHistory() {
    return {
      status: 'ready',
      data: sampleEnergyHistory(),
      freshness: {
        through: DAILY_ENERGY[DAILY_ENERGY.length - 1]?.[0] ?? TELEMETRY_DAY,
        kind: 'sample',
      },
    };
  },
  async getDayCurve() {
    return curveFromPlan(samplePlan());
  },
};
