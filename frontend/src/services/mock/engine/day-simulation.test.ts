import { describe, expect, it } from 'vitest';
import { SAMPLE_SITE } from '../constants';
import { HOURLY_SOLAR_KW } from '../lhr-res-01';
import { simulateDay } from './day-simulation';

const day = simulateDay();
const inPeak = (hour: number) =>
  hour >= SAMPLE_SITE.peakStartHour && hour < SAMPLE_SITE.peakEndHour;

describe('simulateDay', () => {
  it('is deterministic', () => {
    expect(simulateDay()).toEqual(day);
  });

  it('produces 24 hourly values for every series', () => {
    for (const series of Object.values(day)) expect(series).toHaveLength(24);
  });

  it('generates no meaningful solar at night', () => {
    for (let hour = 0; hour < 24; hour++) {
      if (hour < 6 || hour > 17) expect(day.solar[hour]).toBeLessThan(0.05);
    }
  });

  it('peaks at the recorded midday output', () => {
    expect(Math.max(...day.solar)).toBe(Math.max(...HOURLY_SOLAR_KW));
  });

  it('keeps battery level between the outage reserve and full', () => {
    const floorPct = (SAMPLE_SITE.reserveFloorKwh / SAMPLE_SITE.batteryCapacityKwh) * 100;
    for (const soc of day.soc) {
      expect(soc).toBeGreaterThanOrEqual(floorPct);
      expect(soc).toBeLessThanOrEqual(100);
    }
  });

  it('never charges faster than the charge limit', () => {
    for (const charge of day.charge) expect(charge).toBeLessThanOrEqual(SAMPLE_SITE.maxChargeKw);
  });

  it('only discharges inside the evening peak', () => {
    for (let hour = 1; hour < 24; hour++) {
      const drop = (day.soc[hour - 1] as number) - (day.soc[hour] as number);
      if (!inPeak(hour)) expect(drop).toBeLessThanOrEqual(0);
    }
  });

  it('covers usage with solar, battery and grid in every hour', () => {
    for (let hour = 0; hour < 24; hour++) {
      const load = day.load[hour] as number;
      const solarToHome = Math.min(day.solar[hour] as number, load);
      // Whatever solar cannot cover is met by the battery (peak only) or the grid.
      const unmet = load - solarToHome - (day.grid[hour] as number);
      expect(unmet).toBeGreaterThanOrEqual(-0.011);
      if (!inPeak(hour)) expect(unmet).toBeLessThanOrEqual(0.011);
    }
  });
});
