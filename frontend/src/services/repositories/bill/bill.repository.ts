import type { BillToolsDefaults } from '@/types/domain/tariff';

export interface BillRepository {
  /** Starting values for the bill forms, taken from the customer's tariff settings. */
  getDefaults(): Promise<BillToolsDefaults>;
}
