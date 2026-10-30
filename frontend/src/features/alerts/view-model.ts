import type { IconName } from '@/components/ui/icon-paths';
import type { Alert, AlertSeverity } from '@/types/domain/alerts';

export type AlertFilter = 'all' | AlertSeverity;

export const SEVERITY: Record<AlertSeverity, { label: string; icon: IconName }> = {
  crit: { label: 'Critical', icon: 'alert' },
  warn: { label: 'Warning', icon: 'alert' },
  info: { label: 'Info', icon: 'info' },
  ok: { label: 'Good news', icon: 'check' },
};

export const FILTERS: ReadonlyArray<{ value: AlertFilter; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'crit', label: 'Critical' },
  { value: 'warn', label: 'Warnings' },
  { value: 'info', label: 'Info' },
  { value: 'ok', label: 'Good news' },
];

export function countFor(alerts: Alert[], filter: AlertFilter): number {
  return filter === 'all' ? alerts.length : alerts.filter((a) => a.severity === filter).length;
}

export function filterAlerts(alerts: Alert[], filter: AlertFilter): Alert[] {
  return filter === 'all' ? alerts : alerts.filter((a) => a.severity === filter);
}
