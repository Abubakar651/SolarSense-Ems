import { shortDate } from '@/lib/dates';
import type { FlowValues } from '@/components/charts/flow-diagram';
import type { InverterLive, Reading } from '@/types/domain/inverter';

const MISSING = '—';

/** A reading with its unit, or a dash when the inverter did not report it. */
export function reading(value: Reading, unit: string, digits = 1): string {
  return value === null ? MISSING : `${value.toFixed(digits)} ${unit}`;
}

const kw = (watts: number) => `${(Math.abs(watts) / 1000).toFixed(2)} kW`;

/** Battery power is positive while charging and negative while discharging. */
export function batteryFlow(batteryPowerW: number): string {
  if (batteryPowerW > 0) return `Charging at ${kw(batteryPowerW)}`;
  if (batteryPowerW < 0) return `Discharging at ${kw(batteryPowerW)}`;
  return 'Idle';
}

/** Grid power is positive while exporting and negative while importing; no grid means a blackout. */
export function gridFlow(data: Pick<InverterLive, 'gridActivePowerW' | 'isGridConnected'>): string {
  if (!data.isGridConnected) return 'Grid is down';
  if (data.gridActivePowerW > 0) return `Exporting ${kw(data.gridActivePowerW)}`;
  if (data.gridActivePowerW < 0) return `Importing ${kw(data.gridActivePowerW)}`;
  return 'Not exchanging power';
}

/** "2026-10-27T02:10:00+05:00" -> "Oct 27, 02:10" (the inverter's own local time). */
export function readingTime(timestamp: string): string {
  return `${shortDate(timestamp.slice(0, 10))}, ${timestamp.slice(11, 16)}`;
}

/** Inverter sign conventions: battery power + is charging, grid power + is exporting. */
export function flowValues(data: InverterLive): FlowValues {
  return {
    solarKw: data.totalPvPowerW / 1000,
    loadKw: data.houseConsumptionW / 1000,
    chargeKw: Math.max(0, data.batteryPowerW) / 1000,
    gridKw: Math.max(0, -data.gridActivePowerW) / 1000,
    exportKw: Math.max(0, data.gridActivePowerW) / 1000,
    soc: Math.round(data.batterySocPct),
  };
}
