import type { PeakWindow } from '@/lib/tariff';

export interface TariffRepository {
  /** The four seasonal peak windows, in the order the Settings screen shows them. */
  getPeakWindows(): Promise<PeakWindow[]>;
}
