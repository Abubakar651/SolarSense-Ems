import type { PeakWindow } from '@/lib/tariff';

/**
 * docs/lesco_residential_tariffs_config_2026.json, topic B "seasonal_peak_windows_pkt".
 * This is sample data for mock mode only: the app reads the same table from
 * GET /api/v2/tariff/peak-window (one month per call) when mocks are off.
 */
export const SAMPLE_PEAK_WINDOWS: readonly PeakWindow[] = [
  { season: 'Winter', months: [12, 1, 2], startHour: 17, endHour: 21 },
  { season: 'Spring', months: [3, 4, 5], startHour: 18, endHour: 22 },
  { season: 'Summer', months: [6, 7, 8], startHour: 19, endHour: 23 },
  { season: 'Autumn', months: [9, 10, 11], startHour: 18, endHour: 22 },
];

/** The sample peak window for a calendar month (1 = January). */
export function peakWindowForMonth(month: number): PeakWindow {
  const window = SAMPLE_PEAK_WINDOWS.find((w) => w.months.includes(month));
  if (!window) throw new RangeError(`Month must be 1 to 12, got ${month}`);
  return window;
}
