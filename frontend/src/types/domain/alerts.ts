export type AlertSeverity = 'crit' | 'warn' | 'info' | 'ok';

export interface Alert {
  id: string;
  severity: AlertSeverity;
  title: string;
  detail: string;
  /** Display time, e.g. "Today, 15:45". */
  when: string;
  unread: boolean;
}
