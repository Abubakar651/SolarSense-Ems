import { TARIFF } from './lhr-res-01';

export interface EnergyValue {
  /** PKR saved compared with buying everything from the grid. */
  totalPkr: number;
  /** The part of it that is export credit. */
  exportPkr: number;
}

/** PKR per kWh that logged energy is valued at. Live: the backend tariff engine's rates for the user's tariff. */
export interface EnergyRates {
  /** A kWh of solar used at home: the import it avoids. */
  selfConsumedPkrPerKwh: number;
  /** A kWh sent to the grid: the regime's export credit. */
  exportPkrPerKwh: number;
}

/** The sample site's rates, for the bundled sample data only. */
export const SAMPLE_RATES: EnergyRates = {
  selfConsumedPkrPerKwh: TARIFF.offPeakPkrPerKwh,
  exportPkrPerKwh: TARIFF.exportPkrPerKwh,
};

/**
 * Energy the home did not buy from the grid is valued at the self-consumption (off-peak or slab) rate,
 * which is the cautious choice because the daily data has no peak/off-peak split. Energy sent to the grid
 * earns the export rate.
 */
export function valueOfEnergy(
  loadKwh: number,
  importedKwh: number,
  exportedKwh: number,
  rates: EnergyRates,
): EnergyValue {
  const exportPkr = exportedKwh * rates.exportPkrPerKwh;
  const totalPkr = Math.max(0, loadKwh - importedKwh) * rates.selfConsumedPkrPerKwh + exportPkr;
  return { totalPkr: Math.round(totalPkr), exportPkr: Math.round(exportPkr) };
}
