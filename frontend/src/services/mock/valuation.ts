import { TARIFF } from './lhr-res-01';

export interface EnergyValue {
  /** PKR saved compared with buying everything from the grid. */
  totalPkr: number;
  /** The part of it that is export credit. */
  exportPkr: number;
}

/**
 * Energy the home did not buy from the grid is valued at the off-peak rate, which is the cautious
 * choice because the data has no peak/off-peak split. Energy sent to the grid earns the export rate.
 */
export function valueOfEnergy(
  loadKwh: number,
  importedKwh: number,
  exportedKwh: number,
): EnergyValue {
  const exportPkr = exportedKwh * TARIFF.exportPkrPerKwh;
  const totalPkr = Math.max(0, loadKwh - importedKwh) * TARIFF.offPeakPkrPerKwh + exportPkr;
  return { totalPkr: Math.round(totalPkr), exportPkr: Math.round(exportPkr) };
}
