import { describe, expect, it } from 'vitest';
import {
  MIN_RESERVE_PCT,
  PROSUMER_REGIMES,
  SEASONAL_PEAK_WINDOWS,
  TARIFF_CATEGORIES,
  peakWindowForMonth,
  regimeInfo,
} from './tariff';

describe('peakWindowForMonth', () => {
  it.each([
    [1, 17, 21],
    [2, 17, 21],
    [3, 18, 22],
    [5, 18, 22],
    [6, 19, 23],
    [8, 19, 23],
    [9, 18, 22],
    [11, 18, 22],
    [12, 17, 21],
  ])('month %i peaks from %i:00 to %i:00', (month, start, end) => {
    const window = peakWindowForMonth(month);
    expect([window.startHour, window.endHour]).toEqual([start, end]);
  });

  it('covers every month exactly once, each with a four-hour window', () => {
    const months = SEASONAL_PEAK_WINDOWS.flatMap((w) => [...w.months]).sort((a, b) => a - b);
    expect(months).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
    expect(SEASONAL_PEAK_WINDOWS.every((w) => w.endHour - w.startHour === 4)).toBe(true);
  });

  it.each([0, 13, 1.5])('rejects month %s', (month) => {
    expect(() => peakWindowForMonth(month)).toThrow(RangeError);
  });
});

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
