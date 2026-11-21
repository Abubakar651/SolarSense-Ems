import { todayInKarachi } from '@/lib/freshness';
import { longDate } from '@/lib/dates';
import type { OutageData } from '@/types/domain/outage';

export type RiskLevel = 'Low' | 'Medium' | 'High';

/** Under 15% is low, 15-30% medium, over 30% high. */
export function riskLevel(pct: number): 0 | 1 | 2 {
  return pct > 30 ? 2 : pct >= 15 ? 1 : 0;
}

export const RISK_LABEL: Record<0 | 1 | 2, RiskLevel> = { 0: 'Low', 1: 'Medium', 2: 'High' };

/** A same-shaped outage history of all zeros, for the Outage screen while the site has none yet. */
export function zeroOutageData(): OutageData {
  return {
    riskByHour: Array.from({ length: 24 }, () => 0),
    recent: [],
    since: longDate(todayInKarachi(new Date())),
    totalCount: 0,
    thisMonth: { count: 0, hours: 0, hitReserve: 0 },
  };
}
