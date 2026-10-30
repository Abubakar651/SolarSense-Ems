import type { OutageData } from '@/types/domain/outage';

export interface OutageRepository {
  getOutage(): Promise<OutageData>;
}
