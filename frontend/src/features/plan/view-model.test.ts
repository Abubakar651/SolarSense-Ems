import { readyPlan } from '@/lib/history';
import { describe, expect, it } from 'vitest';
import { energyMock } from '@/services/repositories/energy/energy.mock';
import { advisoryMock } from '@/services/repositories/advisory/advisory.mock';
import { zeroDayPlan } from '@/features/dashboard/view-model';
import { briefStats, generationModeLabel, metricRows, planSummary } from './view-model';

const plan = readyPlan(await energyMock.getDayPlan());
const summary = planSummary(plan);

describe('planSummary', () => {
  it('states how much of the evening peak the battery covers', () => {
    expect(summary.bannerTitle).toMatch(
      /^Tonight, the battery covers \d+% of your peak-hour usage$/,
    );
  });

  it('splits peak usage between battery and grid so the parts add up', () => {
    const [, usage, battery, grid] = summary.bannerDetail.match(
      /([\d.]+) kWh used: battery ([\d.]+), grid ([\d.]+)/,
    ) as RegExpMatchArray;
    expect(Number(battery) + Number(grid)).toBeCloseTo(Number(usage), 1);
  });

  it('mentions the outage reserve as a share of the battery', () => {
    expect(summary.bannerDetail).toContain('15% kept for outages');
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

  it('never shows "NaN" for an all-zero plan', () => {
    const zeroSummary = planSummary(zeroDayPlan());
    expect(zeroSummary.bannerTitle).not.toContain('NaN');
    expect(zeroSummary.bannerDetail).not.toContain('NaN');
    expect(zeroSummary.gridSub).toBe('No grid power needed');
  });
});

const sampleBrief = await advisoryMock.getAdvisory();
if (sampleBrief.status !== 'ready') throw new Error('The sample brief is always ready');
const { advisory } = sampleBrief;

describe('advisory brief', () => {
  it('is the labelled sample brief in mock mode', () => {
    expect(advisory.isSample).toBe(true);
  });

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

describe('briefStats', () => {
  it('shows a dash for a figure the sample plan cannot work out', () => {
    const stats = briefStats(advisory);
    const savings = stats.find((s) => s.title === 'Peak-hour savings');
    expect(savings?.value).toBe('—');
    expect(savings?.unit).toBeUndefined();
  });

  it('reports zero outage hours as "No blackouts today"', () => {
    const stats = briefStats({ ...advisory, keyMetrics: { ...advisory.keyMetrics, outageHours: 0 } });
    const outage = stats.find((s) => s.title === 'Outage backup');
    expect(outage?.value).toBe('0');
    expect(outage?.sub).toBe('No blackouts today');
  });

  it('formats a populated savings figure with separators', () => {
    const stats = briefStats({
      ...advisory,
      keyMetrics: { ...advisory.keyMetrics, netSavingsPkr: 12345.6 },
    });
    const savings = stats.find((s) => s.title === 'Peak-hour savings');
    expect(savings?.value).toBe('12,346');
    expect(savings?.unit).toBe('PKR');
  });
});
