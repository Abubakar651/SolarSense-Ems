import type { Alert } from '@/types/domain/alerts';
import { durationLabel, shortDate } from '@/lib/dates';
import { ALARMS, TELEMETRY_DAY, type InverterAlarm } from '../../mock/lhr-res-01';
import type { AlertsRepository } from './alerts.repository';

/** A grid outage lasting at least this long is critical; shorter ones are warnings. */
const CRITICAL_MINUTES = 15;

/**
 * The inverter reports one grid loss as several alarms (under-voltage, frequency, protection trips) that
 * fall inside the same window. They are folded into one alert per "Grid Power Outage" alarm.
 */
function toAlert(outage: InverterAlarm): Alert {
  const related = ALARMS.filter(
    (alarm) => alarm !== outage && alarm.start >= outage.start && alarm.end <= outage.end,
  );
  const date = outage.start.slice(0, 10);
  const minutes = Math.round(outage.minutes);
  const faults = [outage.name, ...related.map((alarm) => alarm.name)].join(', ');

  return {
    id: `grid-loss-${outage.start.replace(/\D/g, '')}`,
    severity: minutes >= CRITICAL_MINUTES ? 'crit' : 'warn',
    title: `Grid outage ${outage.status.toLowerCase()}`,
    detail: `Grid power was lost for ${durationLabel(minutes)}. Inverter faults: ${faults}.`,
    when: `${shortDate(date)}, ${outage.start.slice(11, 16)}`,
    unread: date === TELEMETRY_DAY,
  };
}

/** Real inverter alarms from data/raw/goodwe_inverter_reports, newest first. */
const SAMPLE_ALERTS: Alert[] = ALARMS.filter((alarm) =>
  alarm.name.includes('Grid Power Outage'),
).map(toAlert);

export const alertsMock: AlertsRepository = {
  async listAlerts() {
    return structuredClone(SAMPLE_ALERTS);
  },
};
