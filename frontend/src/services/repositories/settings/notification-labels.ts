import type { NotificationKey } from '@/types/domain/settings';

/** What each alert type is called on the Notifications tab. */
export const NOTIFICATION_LABELS: Record<NotificationKey, string> = {
  grid_outage: 'Grid outage starts or ends',
  outage_risk: 'High outage risk tonight',
  peak_soon: 'Peak hours starting soon',
  panels_dirty: 'Panels need cleaning',
  inverter_offline: 'Inverter offline',
  weekly_digest: 'Weekly savings digest',
};
