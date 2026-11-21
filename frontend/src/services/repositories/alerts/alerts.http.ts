import { shortDate } from '@/lib/dates';
import type { Alert } from '@/types/domain/alerts';
import { apiGet } from '../../http/client';
import type { AlertDto } from '../../http/dto';
import type { AlertsRepository } from './alerts.repository';

const SITE_TIME_ZONE = 'Asia/Karachi';

const PARTS = new Intl.DateTimeFormat('en-CA', {
  timeZone: SITE_TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

/** "2026-10-27T09:30:00Z" -> "Oct 27, 14:30" (site local time, same format as the mock alerts). */
export function alertWhen(isoUtc: string): string {
  const parts = Object.fromEntries(
    PARTS.formatToParts(new Date(isoUtc)).map((p) => [p.type, p.value]),
  );
  return `${shortDate(`${parts.year}-${parts.month}-${parts.day}`)}, ${parts.hour}:${parts.minute}`;
}

export function toAlert(dto: AlertDto): Alert {
  return {
    id: dto.id,
    severity: dto.severity,
    title: dto.title,
    detail: dto.detail,
    when: alertWhen(dto.created_at),
    unread: !dto.read,
  };
}

export const alertsHttp: AlertsRepository = {
  async listAlerts() {
    return (await apiGet<AlertDto[]>('/api/alerts')).map(toAlert);
  },
};
