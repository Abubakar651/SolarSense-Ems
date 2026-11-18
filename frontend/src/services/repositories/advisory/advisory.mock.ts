import type { Advisory } from '@/types/domain/advisory';
import { pad } from '@/lib/format';
import { OUTAGES } from '../../mock/lhr-res-01-history';
import { SOILING, TARIFF, TELEMETRY_DAY } from '../../mock/lhr-res-01';
import { energyMock } from '../energy/energy.mock';
import { panelsMock } from '../panels/panels.mock';
import type { AdvisoryRepository } from './advisory.repository';

const sum = (values: readonly number[]) => values.reduce((a, b) => a + b, 0);
const round = (value: number, digits = 2) => Number(value.toFixed(digits));

/**
 * A brief built from the sample day's own numbers (the replayed plan, the recorded outages and the
 * soiling model), worded like the backend's. It is not the backend's text and no solver ran.
 */
async function buildAdvisory(): Promise<Advisory> {
  const plan = await energyMock.getDayPlan();
  const soiling = await panelsMock.getSoiling();
  // The same sum the panels screen shows (features/panels/view-model.ts), repeated here because
  // services must not import from features.
  const washDays = Math.min(soiling.daysUntilRain ?? soiling.horizonDays, soiling.horizonDays);
  const dustLossPkr = soiling.dailyLossKwh * soiling.tariffPkrPerKwh * washDays;
  const washNetPkr = dustLossPkr - soiling.defaultWashCostPkr;
  const washPaysOff = washNetPkr > 0;

  const peakHours = plan.load
    .map((_, hour) => hour)
    .filter((hour) => hour >= plan.peakStartHour && hour < plan.peakEndHour);
  const peakLoad = sum(peakHours.map((hour) => plan.load[hour] as number));
  const peakGrid = sum(peakHours.map((hour) => plan.grid[hour] as number));
  const peakDischarge = peakLoad - peakGrid;
  const window = `${pad(plan.peakStartHour)}:00–${pad(plan.peakEndHour)}:00`;

  const outages = OUTAGES.filter(([date]) => date === TELEMETRY_DAY);
  const outageMinutes = sum(outages.map(([, , , minutes]) => minutes));
  const reservePct = Math.round((plan.reserveFloorKwh / plan.batteryCapacityKwh) * 100);

  const dayLabel = TELEMETRY_DAY;
  return {
    date: dayLabel,
    headline: `The battery covers ${Math.round((peakDischarge / peakLoad) * 100)}% of your ${window} usage and ${
      washPaysOff ? 'a panel wash pays for itself' : 'panels can wait for rain'
    }.`,
    dispatchArbitrageBrief:
      `Peak hours (${window}) cost PKR ${TARIFF.peakPkrPerKwh}/kWh against PKR ${TARIFF.offPeakPkrPerKwh} off-peak. ` +
      `Your home uses ${peakLoad.toFixed(1)} kWh in that window; the battery supplies ${peakDischarge.toFixed(1)} kWh ` +
      `and the grid ${peakGrid.toFixed(1)} kWh. The battery charges from solar only during peak hours.`,
    blackoutResilienceBrief:
      outages.length === 0
        ? `No outage on record for this day. ${reservePct}% of the battery stays reserved for one.`
        : `${outages.length} outage of 15 minutes or more was recorded (${outageMinutes} min in total). ` +
          `${reservePct}% of the battery stays reserved, and the inverter does not export while the grid is down.`,
    soilingMaintenanceBrief:
      `Dust cost about ${soiling.dailyLossKwh} kWh a day since the wash on ${SOILING.washDate}. ` +
      `Over the next ${washDays} days that is PKR ${Math.round(dustLossPkr)} against a PKR ${soiling.defaultWashCostPkr} wash.`,
    recommendedActions: [
      `Keep the battery charging from solar before ${pad(plan.peakStartHour)}:00.`,
      `Leave the ${reservePct}% outage reserve untouched.`,
      washPaysOff
        ? 'Book a panel wash: it pays for itself before the next rain.'
        : 'Hold off on cleaning panels until the forecast rain.',
    ],
    keyMetrics: {
      solarGenerationKwh: round(sum(plan.solar)),
      householdLoadKwh: round(sum(plan.load)),
      gridImportKwh: round(sum(plan.grid)),
      netMeteringExportKwh: null,
      exportRevenuePkr: null,
      peakBatteryDischargeKwh: round(peakDischarge),
      outageHours: round(outageMinutes / 60),
      netSavingsPkr: null,
      soilingLossKwh: soiling.dailyLossKwh,
      netCleaningBenefitPkr: Math.round(washNetPkr),
    },
    generationMode: 'sample_from_recorded_day',
    isSample: true,
  };
}

export const advisoryMock: AdvisoryRepository = {
  async getAdvisory() {
    return buildAdvisory();
  },
};
