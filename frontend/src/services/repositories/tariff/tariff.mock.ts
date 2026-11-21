import type { PeakWindow } from '@/lib/tariff';
import { SAMPLE_PEAK_WINDOWS } from '../../mock/tariff-windows';
import type { TariffRepository } from './tariff.repository';

export const tariffMock: TariffRepository = {
  async getPeakWindows(): Promise<PeakWindow[]> {
    return SAMPLE_PEAK_WINDOWS.map((window) => ({ ...window, months: [...window.months] }));
  },
};
