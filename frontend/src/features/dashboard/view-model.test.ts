import { describe, expect, it } from 'vitest';
import { energyMock } from '@/services/repositories/energy/energy.mock';
import { dashboardSnapshot } from './view-model';

const plan = await energyMock.getDayPlan();
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

  it('says "Now" once the peak has started', () => {
    expect(at(18, 0).peakCountdown).toBe('Now');
    expect(at(20, 30).peakCountdown).toBe('Now');
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
