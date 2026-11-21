import type { CleanEvent, SoilingData } from '@/types/domain/panels';
import { longDate } from '@/lib/dates';
import { SOILING, TARIFF } from '../../mock/lhr-res-01';
import type { PanelsRepository } from './panels.repository';

const FORECAST_DAYS = 4;
const HORIZON_DAYS = 14;
const round1 = (value: number) => Math.round(value * 10) / 10;

/** The soiling model since the panels were last cleaned (the input buildSoiling needs). */
export interface SoilingInput {
  /** Day of the clean event (a wash, or washing rain). */
  washDate: string;
  cleanEvent: CleanEvent;
  asOf: string;
  /** Model performance ratio for each day from the clean event to asOf. */
  modelPr: readonly number[];
  dailyLossKwh: number;
  /** What one kWh lost to dust costs at the site's tariff. */
  tariffPkrPerKwh: number;
  /** Default price of one wash for the calculator. */
  washCostPkr: number;
}

/** The rain outlook buildSoiling needs. `available` is false when the forecast could not be fetched. */
export interface RainOutlook {
  available: boolean;
  /** Days until rain that washes the panels; null when none is forecast (or none is known). */
  daysUntilRain: number | null;
}

/** The sample site's soiling model, valued at its sample tariff and wash price. */
const SAMPLE_SOILING: SoilingInput = {
  ...SOILING,
  cleanEvent: 'wash',
  tariffPkrPerKwh: TARIFF.offPeakPkrPerKwh,
  washCostPkr: TARIFF.washCostPkr,
};

/** Stands in for the backend's Open-Meteo rain forecast (GET /api/insights/rain). */
export const SAMPLE_RAIN: RainOutlook = { available: true, daysUntilRain: 6 };

/** The Panels screen from the soiling model. Shared by the sample data and the API repository. */
export function buildSoiling(soiling: SoilingInput, rain: RainOutlook): SoilingData {
  const { modelPr } = soiling;
  /** Percent of output lost relative to the model's clean value on wash day. */
  const lossPct = (pr: number) => round1((1 - pr / (modelPr[0] as number)) * 100);
  const latest = modelPr.length - 1;
  // The model decays by a constant factor per day, so the next days continue the same curve.
  const dailyFactor = (modelPr[latest] as number) / (modelPr[latest - 1] as number);
  const forecast = Array.from({ length: FORECAST_DAYS }, (_, i) =>
    lossPct((modelPr[latest] as number) * dailyFactor ** (i + 1)),
  );

  return {
    history: modelPr.map(lossPct),
    forecast,
    asOf: longDate(soiling.asOf),
    lastWashed: longDate(soiling.washDate),
    cleanEvent: soiling.cleanEvent,
    defaultWashCostPkr: soiling.washCostPkr,
    dailyLossKwh: soiling.dailyLossKwh,
    tariffPkrPerKwh: soiling.tariffPkrPerKwh,
    horizonDays: HORIZON_DAYS,
    daysUntilRain: rain.available ? rain.daysUntilRain : null,
    rainForecastAvailable: rain.available,
  };
}

export const panelsMock: PanelsRepository = {
  async getSoiling() {
    return {
      status: 'ready',
      data: buildSoiling(SAMPLE_SOILING, SAMPLE_RAIN),
      freshness: { through: SOILING.asOf, kind: 'sample' },
    };
  },
};
