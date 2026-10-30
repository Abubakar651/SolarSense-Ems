export type RiskLevel = 'Low' | 'Medium' | 'High';

/** Under 15% is low, 15-30% medium, over 30% high. */
export function riskLevel(pct: number): 0 | 1 | 2 {
  return pct > 30 ? 2 : pct >= 15 ? 1 : 0;
}

export const RISK_LABEL: Record<0 | 1 | 2, RiskLevel> = { 0: 'Low', 1: 'Medium', 2: 'High' };
