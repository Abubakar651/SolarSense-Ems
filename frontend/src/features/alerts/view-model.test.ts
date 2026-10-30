import { describe, expect, it } from 'vitest';
import { alertsMock } from '@/services/repositories/alerts/alerts.mock';
import { countFor, filterAlerts } from './view-model';

const alerts = await alertsMock.listAlerts();

describe('alert filters', () => {
  it('counts every alert under "all"', () => {
    expect(countFor(alerts, 'all')).toBe(alerts.length);
  });

  it('counts and filters by severity consistently', () => {
    for (const severity of ['crit', 'warn', 'info', 'ok'] as const) {
      expect(filterAlerts(alerts, severity)).toHaveLength(countFor(alerts, severity));
      expect(filterAlerts(alerts, severity).every((a) => a.severity === severity)).toBe(true);
    }
  });

  it('returns everything for "all" and keeps the order', () => {
    expect(filterAlerts(alerts, 'all')).toEqual(alerts);
  });

  it('partitions the list: severity counts add up to the total', () => {
    const parts = (['crit', 'warn', 'info', 'ok'] as const).map((s) => countFor(alerts, s));
    expect(parts.reduce((a, b) => a + b, 0)).toBe(alerts.length);
  });
});
