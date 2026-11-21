import { describe, expect, it } from 'vitest';
import { MIN_RESERVE_PCT, PROSUMER_REGIMES, TARIFF_CATEGORIES, regimeInfo } from './tariff';

// The seasonal peak windows now come from the tariff repository: see services/mock/tariff-windows.test.ts
// (sample table) and services/repositories/tariff/tariff.http.test.ts (the API mapping).

describe('prosumer regimes', () => {
  it('credits exports at the backend rate for each regime', () => {
    expect(regimeInfo('GRANDFATHERED_NET_METERING').exportPkrPerKwh).toBe(25.32);
    expect(regimeInfo('NET_BILLING_2026').exportPkrPerKwh).toBe(8.13);
    expect(regimeInfo('SINGLE_PHASE_SLAB_ZERO_EXPORT').exportPkrPerKwh).toBe(0);
    expect(PROSUMER_REGIMES).toHaveLength(3);
  });
});

describe('constants', () => {
  it('offers the five backend tariff categories', () => {
    expect(TARIFF_CATEGORIES.map((c) => c.id)).toEqual([
      'LIFELINE',
      'PROTECTED',
      'UNPROTECTED',
      'TOU_A1B',
      'PREPAID_A1C',
    ]);
  });

  it('holds the battery reserve at the 15% inverter floor', () => {
    expect(MIN_RESERVE_PCT).toBe(15);
  });
});
