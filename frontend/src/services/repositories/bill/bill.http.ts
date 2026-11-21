import { settingsHttp } from '../settings/settings.http';
import type { BillRepository } from './bill.repository';

/** The bill forms start from the customer's saved tariff settings. */
export const billHttp: BillRepository = {
  async getDefaults() {
    const { tariff } = await settingsHttp.getSettings();
    return {
      sanctionedLoadKw: Number(tariff.sanctionedLoadKw),
      category: tariff.category,
      includeElectricityDuty: tariff.includeElectricityDuty,
      isAtlFiler: tariff.isAtlFiler,
    };
  },
};
