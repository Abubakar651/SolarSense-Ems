import { describe, expect, it } from 'vitest';
import { inverterMock } from '@/services/repositories/inverter/inverter.mock';
import { batteryFlow, flowValues, gridFlow, reading, readingTime } from './view-model';

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

describe('flowValues', () => {
  it('converts inverter sign conventions into flow-diagram values', () => {
    expect(
      flowValues({
        totalPvPowerW: 2400,
        houseConsumptionW: 850,
        batteryPowerW: 1200,
        gridActivePowerW: -600,
        batterySocPct: 73.6,
      } as Parameters<typeof flowValues>[0]),
    ).toEqual({
      solarKw: 2.4,
      loadKw: 0.85,
      chargeKw: 1.2,
      gridKw: 0.6,
      exportKw: 0,
      soc: 74,
    });
  });

  it('reads a discharging battery and exporting grid as zero charge/grid', () => {
    expect(
      flowValues({
        totalPvPowerW: 0,
        houseConsumptionW: 500,
        batteryPowerW: -500,
        gridActivePowerW: 300,
        batterySocPct: 40,
      } as Parameters<typeof flowValues>[0]),
    ).toEqual({
      solarKw: 0,
      loadKw: 0.5,
      chargeKw: 0,
      gridKw: 0,
      exportKw: 0.3,
      soc: 40,
    });
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
});
