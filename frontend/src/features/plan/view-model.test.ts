import { describe, expect, it } from 'vitest';
import { energyMock } from '@/services/repositories/energy/energy.mock';
import { advisoryMock } from '@/services/repositories/advisory/advisory.mock';
import { generationModeLabel, metricRows, planSummary } from './view-model';

const plan = await energyMock.getDayPlan();
const summary = planSummary(plan);

describe('planSummary', () => {
  it('states how much of the evening peak the battery covers', () => {
    expect(summary.bannerTitle).toMatch(
      /^Tonight, the battery covers \d+% of your peak-hour usage$/,
    );
  });

  it('splits peak usage between battery and grid so the parts add up', () => {
    const [, usage, battery, grid] = summary.bannerDetail.match(
      /uses ([\d.]+) kWh\. The battery supplies ([\d.]+) kWh and the grid the remaining ([\d.]+) kWh/,
    ) as RegExpMatchArray;
    expect(Number(battery) + Number(grid)).toBeCloseTo(Number(usage), 1);
  });

  it('mentions the outage reserve as a share of the battery', () => {
    expect(summary.bannerDetail).toContain('The last 15% of the battery is kept back for outages');
  });

  it('totals the day to one decimal', () => {
    expect(summary.solarKwh).toMatch(/^\d+\.\d$/);
    expect(Number(summary.loadKwh)).toBeGreaterThan(Number(summary.gridKwh));
  });

  it('produces one table row per hour with five columns', () => {
    expect(summary.tableRows).toHaveLength(24);
    expect(summary.tableRows[0]).toHaveLength(5);
    expect(summary.tableRows[23]?.[0]).toBe('23:00');
  });
});

const advisory = await advisoryMock.getAdvisory();

describe('advisory brief', () => {
  it('carries the ten figures the backend sends, in a fixed order', () => {
    expect(Object.keys(advisory.keyMetrics)).toEqual([
      'solarGenerationKwh',
      'householdLoadKwh',
      'gridImportKwh',
      'netMeteringExportKwh',
      'exportRevenuePkr',
      'peakBatteryDischargeKwh',
      'outageHours',
      'netSavingsPkr',
      'soilingLossKwh',
      'netCleaningBenefitPkr',
    ]);
    expect(metricRows(advisory.keyMetrics)).toHaveLength(10);
  });

  it('builds its figures from the same plan the screen shows', () => {
    // The screen rounds to one decimal, so allow half a tenth (plus float noise).
    const within = (actual: number, shown: string) =>
      Math.abs(actual - Number(shown)) <= 0.05 + 1e-9;
    expect(within(advisory.keyMetrics.solarGenerationKwh, summary.solarKwh)).toBe(true);
    expect(within(advisory.keyMetrics.gridImportKwh, summary.gridKwh)).toBe(true);
  });

  it('shows a dash, not 0, for a figure the sample plan cannot work out', () => {
    const rows = Object.fromEntries(metricRows(advisory.keyMetrics));
    expect(rows['Sent to the grid']).toBe('—');
    expect(rows['Saved by the plan']).toBe('—');
  });

  it('formats money with separators and energy with one decimal', () => {
    const rows = Object.fromEntries(
      metricRows({ ...advisory.keyMetrics, exportRevenuePkr: 12345.6, solarGenerationKwh: 25.61 }),
    );
    expect(rows['Export credit']).toBe('12,346 PKR');
    expect(rows['Solar generated']).toBe('25.6 kWh');
  });

  it('turns the generation mode into words', () => {
    expect(generationModeLabel('deterministic_physics_synthesizer')).toBe(
      'Deterministic physics synthesizer',
    );
  });
});
