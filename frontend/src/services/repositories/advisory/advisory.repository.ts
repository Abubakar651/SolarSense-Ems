import type { AdvisoryResult } from '@/types/domain/advisory';

export interface AdvisoryRepository {
  /** The written brief for today's plan, or "unavailable" when it can't be written right now. */
  getAdvisory(): Promise<AdvisoryResult>;
}
