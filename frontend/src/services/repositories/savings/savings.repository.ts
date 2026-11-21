import type { HistoryResult } from '@/types/domain/history';
import type { SavingsData } from '@/types/domain/savings';

export interface SavingsRepository {
  getSavings(): Promise<HistoryResult<SavingsData>>;
}
