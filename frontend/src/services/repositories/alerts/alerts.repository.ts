import type { Alert } from '@/types/domain/alerts';

export interface AlertsRepository {
  /** Newest first. */
  listAlerts(): Promise<Alert[]>;
}
