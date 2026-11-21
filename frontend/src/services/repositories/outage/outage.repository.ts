import type { HistoryResult } from '@/types/domain/history';
import type { OutageData } from '@/types/domain/outage';

export interface OutageRepository {
  getOutage(): Promise<HistoryResult<OutageData>>;
}
