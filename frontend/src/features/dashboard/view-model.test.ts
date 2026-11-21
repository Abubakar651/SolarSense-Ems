import { readyPlan } from '@/lib/history';
import { describe, expect, it } from 'vitest';
import { energyMock } from '@/services/repositories/energy/energy.mock';
import { inverterMock } from '@/services/repositories/inverter/inverter.mock';
import type { InverterLive, InverterReading } from '@/types/domain/inverter';
import { dashboardSnapshot, forecastNote } from './view-model';

const plan = readyPlan(await energyMock.getDayPlan());
const at = (hour: number, minute = 0) => dashboardSnapshot(plan, { hour, minute });

describe('dashboardSnapshot', () => {
  it('reads the current hour from the plan', () => {
    const snap = at(15, 42);
    expect(snap.solarKw).toBe(plan.solar[15]);
    expect(snap.loadKw).toBe(plan.load[15]);
    expect(snap.soc).toBe(plan.soc[15]);
  });

  it('counts down to the evening peak', () => {
    expect(at(15, 42).peakCountdown).toBe('2h 18m');
    expect(at(17, 59).peakCountdown).toBe('0h 1m');
  });

  it('says "Now" while the peak lasts and "Ended" after it', () => {
    expect(at(18, 0).peakCountdown).toBe('Now');
    expect(at(20, 30).peakCountdown).toBe('Now');
    expect(at(plan.peakEndHour, 5).peakCountdown).toBe('Ended');
  });

  it("names the plan's own peak start and the level planned for it", () => {
    const winter = { ...plan, peakStartHour: 17, peakEndHour: 21, soc: plan.soc.map((_, h) => (h === 16 ? 77 : 40)) };
    const snap = dashboardSnapshot(winter, { hour: 10, minute: 0 });
    expect(snap.peakNote).toBe('Battery should reach about 77% by 17:00.');
  });

  it('describes a full battery as ready for the peak', () => {
    const snap = at(15, 42);
    expect(snap.soc).toBe(100);
    expect(snap.batterySub).toBe('Full. Ready for peak hours');
    expect(snap.peakNote).toBe('Battery is full and ready for the evening peak.');
  });

  it('reports charging power while solar tops up the battery', () => {
    const snap = at(9);
    expect(snap.chargeKw).toBeGreaterThan(0);
    expect(snap.batterySub).toBe(`Charging at ${snap.chargeKw.toFixed(1)} kW from solar`);
  });

  it('never exports more solar than is left after home and battery', () => {
    for (let hour = 0; hour < 24; hour++) {
      const snap = at(hour);
      expect(snap.exportKw).toBeGreaterThanOrEqual(0);
      expect(snap.exportKw).toBeLessThanOrEqual(snap.solarKw);
    }
  });

  it('says no grid power is used when the grid is idle', () => {
    expect(at(12).flowSummary.endsWith('. No grid power is being used.')).toBe(true);
  });

  it('gives a non-negative backup time that shrinks with a lower battery level', () => {
    expect(Number(at(15).backupHours)).toBeGreaterThan(Number(at(3).backupHours));
    for (let hour = 0; hour < 24; hour++)
      expect(Number(at(hour).backupHours)).toBeGreaterThanOrEqual(0);
  });
});

const sample = await inverterMock.getLive();
if (sample.status !== 'online') throw new Error('The inverter mock should be online');

/** An online reading with the given measured values (battery + = charging, grid + = exporting). */
const reading = (data: Partial<InverterLive>): InverterReading => ({
  ...sample,
  isSample: false,
  data: { ...sample.data, ...data },
});

describe('dashboardSnapshot with the inverter', () => {
  const live = reading({
    totalPvPowerW: 3200,
    houseConsumptionW: 1100,
    batteryPowerW: 900,
    gridActivePowerW: 1200,
    batterySocPct: 72.4,
    isBlackout: false,
  });

  it('shows measured power, not the plan', () => {
    const snap = dashboardSnapshot(plan, { hour: 3, minute: 0 }, live);
    expect(snap.source).toBe('live');
    expect([snap.solarKw, snap.loadKw, snap.chargeKw]).toEqual([3.2, 1.1, 0.9]);
    expect(snap.soc).toBe(72);
  });

  it('reads export and import from the sign of grid power', () => {
    expect(dashboardSnapshot(plan, { hour: 12, minute: 0 }, live)).toMatchObject({
      exportKw: 1.2,
      gridKw: 0,
    });
    const importing = reading({ gridActivePowerW: -800 });
    expect(dashboardSnapshot(plan, { hour: 12, minute: 0 }, importing)).toMatchObject({
      exportKw: 0,
      gridKw: 0.8,
    });
  });

  it('describes a discharging battery as powering the home', () => {
    const snap = dashboardSnapshot(
      plan,
      { hour: 20, minute: 0 },
      reading({ batteryPowerW: -1500 }),
    );
    expect(snap.batterySub).toBe('Powering your home at 1.5 kW');
    expect(snap.flowSummary).toContain('the battery supplying 1.5 kW');
  });

  it('sizes the backup from the measured level and usage', () => {
    const snap = dashboardSnapshot(
      plan,
      { hour: 20, minute: 0 },
      reading({ batterySocPct: 50, houseConsumptionW: 1000 }),
    );
    // (0.5 × 5.12 − 0.768) × 0.95 / 1.0
    expect(snap.backupHours).toBe('1.7');
  });

  it("uses the plan's usage for the backup when the inverter reports no load", () => {
    const snap = dashboardSnapshot(
      plan,
      { hour: 20, minute: 0 },
      reading({ houseConsumptionW: 0 }),
    );
    expect(Number.isFinite(Number(snap.backupHours))).toBe(true);
  });

  it('flags a blackout on the grid badge', () => {
    expect(
      dashboardSnapshot(plan, { hour: 9, minute: 0 }, reading({ isBlackout: true })).grid,
    ).toEqual({
      label: 'Grid down',
      tone: 'bad',
    });
    expect(dashboardSnapshot(plan, { hour: 9, minute: 0 }, live).grid.label).toBe('Grid connected');
  });

  it("falls back to the plan's hour and says the inverter is offline when it can't be reached", () => {
    const snap = dashboardSnapshot(
      plan,
      { hour: 15, minute: 0 },
      { status: 'offline', message: 'x' },
    );
    expect(snap.source).toBe('offline');
    expect(snap.grid).toEqual({ label: 'Inverter offline', tone: 'neutral' });
    expect(snap.solarKw).toBe(plan.solar[15]);
  });

  it('keeps sample data on the plan when there is no reading', () => {
    expect(dashboardSnapshot(plan, { hour: 15, minute: 0 }).source).toBe('plan');
  });
});

describe('forecastNote', () => {
  it('explains a forecast whose history is only partly logged', () => {
    const note = forecastNote({ ...plan, forecast: { loggedHistoryHours: 48, historyHours: 192 } });
    expect(note).toContain('Only 2 of the 8 days');
  });

  it('says nothing once the whole history is logged, or for sample data', () => {
    expect(
      forecastNote({ ...plan, forecast: { loggedHistoryHours: 192, historyHours: 192 } }),
    ).toBeNull();
    expect(forecastNote(plan)).toBeNull();
  });

  it('says when the starting battery level was assumed', () => {
    expect(forecastNote({ ...plan, initialSocAssumed: true })).toBe(
      'Starting battery level assumed (no reading near midnight).',
    );
  });
});
