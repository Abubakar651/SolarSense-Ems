import { describe, expect, it } from 'vitest';
import { RISK_LABEL, riskLevel } from './view-model';

describe('riskLevel', () => {
  it.each([
    [0, 0],
    [14, 0],
    [15, 1],
    [30, 1],
    [31, 2],
    [38, 2],
  ])('classifies %s%% as level %s', (pct, level) => {
    expect(riskLevel(pct)).toBe(level);
  });

  it('labels each level', () => {
    expect(Object.values(RISK_LABEL)).toEqual(['Low', 'Medium', 'High']);
  });
});
