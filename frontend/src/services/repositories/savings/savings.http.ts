import { energyResult, fetchEnergyHistory, toEnergyRates } from '../insights.http';
import { buildSavings } from './savings.mock';
import type { SavingsRepository } from './savings.repository';

/**
 * Recorded and logged energy from the API, valued by the same builder as the sample data at the rates the
 * backend's tariff engine gives for the user's own tariff. The month's cost is the engine's bill estimate.
 */
export const savingsHttp: SavingsRepository = {
  async getSavings() {
    const dto = await fetchEnergyHistory();
    return energyResult(dto, (daily, meters, meteredThrough) => {
      const data = buildSavings(daily, meters, meteredThrough, toEnergyRates(dto));
      const month = dto.current_month;
      if (!month) throw new Error('The energy history has no bill estimate for its latest month');
      return {
        ...data,
        currentMonth: {
          ...data.currentMonth,
          costPkr: Math.round(Number(month.cost_pkr)),
          withoutSolarPkr: Math.round(Number(month.without_solar_pkr)),
        },
      };
    });
  },
};
