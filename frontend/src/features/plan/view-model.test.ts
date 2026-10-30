import { describe, expect, it } from 'vitest';
import { energyMock } from '@/services/repositories/energy/energy.mock';
import { planSummary } from './view-model';

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
