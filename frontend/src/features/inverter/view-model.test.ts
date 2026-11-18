import { describe, expect, it } from 'vitest';
import { inverterMock } from '@/services/repositories/inverter/inverter.mock';
import { batteryFlow, energyRows, gridFlow, reading, readingTime } from './view-model';

describe('batteryFlow', () => {
  it('reads positive power as charging and negative as discharging', () => {
    expect(batteryFlow(1200)).toBe('Charging at 1.20 kW');
    expect(batteryFlow(-2500)).toBe('Discharging at 2.50 kW');
    expect(batteryFlow(0)).toBe('Idle');
  });
});

describe('gridFlow', () => {
  it('reads positive power as exporting and negative as importing', () => {
    expect(gridFlow({ gridActivePowerW: 3100, isGridConnected: true })).toBe('Exporting 3.10 kW');
    expect(gridFlow({ gridActivePowerW: -850, isGridConnected: true })).toBe('Importing 0.85 kW');
    expect(gridFlow({ gridActivePowerW: 0, isGridConnected: true })).toBe('Not exchanging power');
  });

  it('reports a blackout whatever the last power was', () => {
    expect(gridFlow({ gridActivePowerW: -850, isGridConnected: false })).toBe('Grid is down');
  });
});

describe('reading', () => {
  it('shows a dash for a value the inverter did not report, not 0', () => {
    expect(reading(null, '°C')).toBe('—');
    expect(reading(0, '°C')).toBe('0.0 °C');
    expect(reading(51.24, 'V')).toBe('51.2 V');
  });
});

describe('readingTime', () => {
  it('shows the inverter local date and time', () => {
    expect(readingTime('2026-10-27T02:10:00+05:00')).toBe('Oct 27, 02:10');
  });
});

const result = await inverterMock.getLive();
if (result.status !== 'online') throw new Error('the sample reading is online');
const { data } = result;

describe('sample reading', () => {
  it('is the last recorded reading, labelled as a sample', () => {
    expect(result.isSample).toBe(true);
    expect(data.batterySocPct).toBe(100);
    expect(data.houseConsumptionW).toBe(850);
  });

  it('flips the recording to the live endpoint signs: importing, battery idle', () => {
    expect(data.gridActivePowerW).toBe(-850);
    expect(gridFlow(data)).toBe('Importing 0.85 kW');
    expect(batteryFlow(data.batteryPowerW)).toBe('Idle');
    expect(Object.is(data.batteryPowerW, -0)).toBe(false);
  });

  it('leaves out readings the recording does not hold', () => {
    expect(data.batterySohPct).toBeNull();
    expect(data.inverterTempRadiatorC).toBeNull();
  });

  it('lists the day totals with the solar and usage figures first', () => {
    expect(energyRows(data).slice(0, 2)).toEqual([
      ['Solar generated', '25.61'],
      ['Home usage', '21.87'],
    ]);
  });
});
