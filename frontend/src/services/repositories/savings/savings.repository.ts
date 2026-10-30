import type { SavingsData } from '@/types/domain/savings';

export interface SavingsRepository {
  getSavings(): Promise<SavingsData>;
}
