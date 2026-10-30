import type { SoilingData } from '@/types/domain/panels';
import { longDate } from '@/lib/dates';
import { SOILING, TARIFF } from '../../mock/lhr-res-01';
import type { PanelsRepository } from './panels.repository';

const FORECAST_DAYS = 4;
const HORIZON_DAYS = 14;
/** Stands in for the backend's Open-Meteo rain forecast (src/forecast/weather_client.py). */
const DAYS_UNTIL_RAIN = 6;
const round1 = (value: number) => Math.round(value * 10) / 10;

/** Percent of output lost on each day since the wash, relative to the model's clean value on wash day. */
const lossPct = (modelPr: number) => round1((1 - modelPr / (SOILING.modelPr[0] as number)) * 100);

function buildSoiling(): SoilingData {
  const { modelPr } = SOILING;
  const latest = modelPr.length - 1;
  // The model decays by a constant factor per day, so the next days continue the same curve.
  const dailyFactor = (modelPr[latest] as number) / (modelPr[latest - 1] as number);
  const forecast = Array.from({ length: FORECAST_DAYS }, (_, i) =>
    lossPct((modelPr[latest] as number) * dailyFactor ** (i + 1)),
  );

  return {
    history: modelPr.map(lossPct),
    forecast,
    asOf: longDate(SOILING.asOf),
    lastWashed: longDate(SOILING.washDate),
    defaultWashCostPkr: TARIFF.washCostPkr,
    dailyLossKwh: SOILING.dailyLossKwh,
    tariffPkrPerKwh: TARIFF.offPeakPkrPerKwh,
    horizonDays: HORIZON_DAYS,
    daysUntilRain: DAYS_UNTIL_RAIN,
  };
}

export const panelsMock: PanelsRepository = {
  async getSoiling() {
    return buildSoiling();
  },
};
