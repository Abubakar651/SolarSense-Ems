import { settingsMock } from '../settings/settings.mock';
import type { BillRepository } from './bill.repository';

export const billMock: BillRepository = {
  async getDefaults() {
    const { tariff } = await settingsMock.getSettings();
    return {
      sanctionedLoadKw: Number(tariff.sanctionedLoadKw),
      category: tariff.category,
      includeElectricityDuty: tariff.includeElectricityDuty,
      isAtlFiler: tariff.isAtlFiler,
    };
  },
};
