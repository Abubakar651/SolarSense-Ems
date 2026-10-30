import { describe, expect, it } from 'vitest';
import { panelsMock } from '@/services/repositories/panels/panels.mock';
import { forecastSeries, paybackDays, parseCost, washAdvice } from './view-model';

const soiling = await panelsMock.getSoiling();

describe('parseCost', () => {
  it.each([
    ['1500', 1500],
    ['Rs 1,500', 1500],
    ['12.5', 12.5],
    ['', 0],
    ['abc', 0],
  ])('reads %j as %s', (input, expected) => {
    expect(parseCost(input)).toBe(expected);
  });
});

describe('washAdvice', () => {
  const dryWeek = { ...soiling, daysUntilRain: null };

  it('prices the dust only until the next rain', () => {
    const advice = washAdvice(soiling, 1500);
    expect(advice.days).toBe(6);
    expect(advice.rainSoon).toBe(true);
    expect(advice.lossPkr).toBeCloseTo(2.207 * 34.53 * 6, 5);
    expect(advice.formula).toBe('2.207 kWh × PKR 34.53 × 6 days = PKR 457');
  });

  it('prices the dust over the whole look-ahead window when no rain is forecast', () => {
    const advice = washAdvice(dryWeek, 1500);
    expect(advice.days).toBe(14);
    expect(advice.rainSoon).toBe(false);
    expect(advice.lossPkr).toBeCloseTo(2.207 * 34.53 * 14, 5);
    expect(advice.formula).toBe('2.207 kWh × PKR 34.53 × 14 days = PKR 1,067');
  });

  it('caps the days at the look-ahead window when the rain is further away', () => {
    const advice = washAdvice({ ...soiling, daysUntilRain: 30 }, 1500);
    expect(advice.days).toBe(14);
    expect(advice.rainSoon).toBe(false);
  });

  it('holds off washing when rain is two days away', () => {
    const advice = washAdvice({ ...soiling, daysUntilRain: 2 }, 1500);
    expect(advice.lossPkr).toBeCloseTo(2.207 * 34.53 * 2, 5);
    expect(advice.wash).toBe(false);
  });

  it('counts no dust loss when it rains today', () => {
    const advice = washAdvice({ ...soiling, daysUntilRain: 0 }, 1);
    expect(advice.lossPkr).toBe(0);
    expect(advice.wash).toBe(false);
  });

  it('recommends washing when cleaning costs less than the dust', () => {
    expect(washAdvice(dryWeek, 500).wash).toBe(true);
    expect(washAdvice(dryWeek, 500).netPkr).toBeCloseTo(567, 0);
  });

  it('recommends waiting when cleaning costs more than the dust', () => {
    expect(washAdvice(dryWeek, 1500).wash).toBe(false);
    expect(washAdvice(dryWeek, 5000).wash).toBe(false);
  });

  it('treats break-even as not worth washing', () => {
    const lossPkr = washAdvice(dryWeek, 0).lossPkr;
    expect(washAdvice(dryWeek, lossPkr).wash).toBe(false);
  });
});

describe('paybackDays', () => {
  it('rounds up to whole days of dust loss', () => {
    expect(paybackDays(soiling, 1500)).toBe(20);
  });
});

describe('soiling history', () => {
  it('starts clean on wash day and grows every day', () => {
    expect(soiling.history[0]).toBe(0);
    for (let day = 1; day < soiling.history.length; day++) {
      expect(soiling.history[day] as number).toBeGreaterThan(soiling.history[day - 1] as number);
    }
  });

  it('is 14 days after the wash on the latest recorded day', () => {
    expect(soiling.history).toHaveLength(15);
  });
});

describe('forecastSeries', () => {
  it('lines up with the history so the two series share the x axis', () => {
    const today = soiling.history.length - 1;
    const series = forecastSeries(soiling);
    expect(series).toHaveLength(soiling.history.length + soiling.forecast.length);
    expect(series.slice(0, today).every((v) => v === null)).toBe(true);
    expect(series[today]).toBe(soiling.history[today]);
  });
});
