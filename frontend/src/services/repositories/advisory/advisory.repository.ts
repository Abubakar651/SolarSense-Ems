import type { Advisory } from '@/types/domain/advisory';

export interface AdvisoryRepository {
  /** The written daily brief for the planned day. */
  getAdvisory(): Promise<Advisory>;
}
