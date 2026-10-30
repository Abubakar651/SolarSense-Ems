import { describe, expect, it } from 'vitest';
import { savingsMock } from '@/services/repositories/savings/savings.mock';
import { savingsSummary } from './view-model';

const data = await savingsMock.getSavings();

describe('savingsSummary', () => {
  it('totals the period and formats it in rupees', () => {
    const total = data.week.values.reduce((a, b) => a + b, 0);
    expect(savingsSummary(data.week).total).toBe(`PKR ${total.toLocaleString('en-US')}`);
  });

  it('averages per period unit', () => {
    expect(savingsSummary(data.week).average).toBe('Average PKR 817 per day');
    expect(savingsSummary(data.year).average).toMatch(/per month$/);
  });

  it('splits the total into home use and export credit whose shares sum to 100%', () => {
    const { breakdown } = savingsSummary(data.month);
    expect(breakdown).toHaveLength(2);
    expect(breakdown.reduce((sum, row) => sum + row.widthPct, 0)).toBeCloseTo(100, 5);
  });

  it('builds one table row per period with the period label capitalised', () => {
    const summary = savingsSummary(data.year);
    expect(summary.tableRows).toHaveLength(12);
    expect(summary.periodLabel).toBe('Month');
    expect(summary.tableRows[0]).toEqual(['Nov', '11,063']);
  });

  it('covers the 30 recorded days up to 7 Oct 2026 for the month view', () => {
    expect(data.month.values).toHaveLength(30);
    expect(data.month.values.every((v) => v > 0)).toBe(true);
  });
});
