import { describe, expect, it } from 'vitest';
import { alertsMock } from './alerts/alerts.mock';
import { energyMock } from './energy/energy.mock';
import { outageMock } from './outage/outage.mock';
import { reportsMock } from './reports/reports.mock';
import { savingsMock } from './savings/savings.mock';
import { settingsMock } from './settings/settings.mock';

describe('site and tariff come from the backend data', () => {
  it('uses the 5.12 kWh battery with a 15% reserve and the LESCO A-1 rates', async () => {
    const plan = await energyMock.getDayPlan();
    expect(plan.batteryCapacityKwh).toBe(5.12);
    expect(plan.reserveFloorKwh / plan.batteryCapacityKwh).toBeCloseTo(0.15, 5);
    expect(plan.tariff).toEqual({ peakPkr: 46.85, offPeakPkr: 34.53, exportPkr: 27 });
  });

  it('describes Station LHR-RES-01 in the settings', async () => {
    const { site, tariff } = await settingsMock.getSettings();
    expect(site).toMatchObject({
      name: 'LHR-RES-01',
      solarKwp: '7.02',
      batteryKwh: '5.12',
      serial: '9010KESC253L0146',
    });
    expect(tariff).toMatchObject({ peakRate: '46.85', offPeakRate: '34.53', exportRate: '27.00' });
  });
});

describe('outages', () => {
  it('lists the newest outage first and counts only outages of 15 minutes or more', async () => {
    const outage = await outageMock.getOutage();
    expect(outage.recent[0]).toMatchObject({ date: 'Oct 26', started: '18:04' });
    expect(outage.recent[1]).toMatchObject({ date: 'Oct 25', duration: '3 h 26 m' });
    expect(outage.totalCount).toBe(56);
  });

  it('gives a percentage for each hour, busiest around 22:00', async () => {
    const { riskByHour } = await outageMock.getOutage();
    expect(riskByHour).toHaveLength(24);
    expect(riskByHour.every((pct) => pct >= 0 && pct <= 100)).toBe(true);
    expect(riskByHour.indexOf(Math.max(...riskByHour))).toBe(22);
  });
});

describe('alerts', () => {
  it('folds the inverter alarms of one grid loss into a single alert, newest first', async () => {
    const alerts = await alertsMock.listAlerts();
    expect(alerts.map((a) => a.when)).toEqual(['Oct 26, 19:27', 'Oct 26, 18:04', 'Oct 25, 21:48']);
    expect(alerts.map((a) => a.severity)).toEqual(['warn', 'crit', 'crit']);
    expect(alerts[2]?.detail).toContain('3 h 26 m');
  });
});

describe('reports', () => {
  it('builds the latest month from the metered station balance', async () => {
    const { months } = await reportsMock.getReport();
    expect(months.map((m) => m.name)).toEqual(['October 2026', 'September 2026', 'August 2026']);
    const october = months[0]!;
    expect(october.coverage).toBe('Metered Oct 1–26');
    expect(october.totals).toEqual([
      { label: 'Solar generated', value: '580 kWh' },
      { label: 'Grid imported', value: '673 kWh' },
      { label: 'Exported', value: '214 kWh' },
      { label: 'Total saved', value: 'PKR 16,179' },
    ]);
  });

  it('only has weekly rows for days with hourly data', async () => {
    const { months } = await reportsMock.getReport();
    expect(months[0]?.weeks.map((w) => w.week)).toEqual(['Oct 1–7']);
    expect(months[2]?.weeks.map((w) => w.week)).toEqual([
      'Aug 1–7',
      'Aug 8–14',
      'Aug 15–21',
      'Aug 22–31',
    ]);
  });
});

describe('savings', () => {
  it('values the year from the monthly meter and the daily views from hourly data', async () => {
    const savings = await savingsMock.getSavings();
    expect(savings.year.values).toHaveLength(12);
    expect(savings.week.values).toHaveLength(7);
    expect(savings.month.values).toHaveLength(30);
    expect(
      savings.year.exportPkr.every((pkr, i) => pkr <= (savings.year.values[i] as number)),
    ).toBe(true);
  });

  it('prices October with and without solar from the same meter figures', async () => {
    const { currentMonth } = await savingsMock.getSavings();
    expect(currentMonth.label).toBe('Oct 1–26');
    expect(currentMonth.withoutSolarPkr - currentMonth.costPkr).toBe(16_178);
    expect(currentMonth.selfPoweredPct).toBe(31);
  });
});
