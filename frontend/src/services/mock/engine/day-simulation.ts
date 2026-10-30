import { SAMPLE_LOAD_KW, SAMPLE_SITE } from '../constants';
import { HOURLY_SOLAR_KW } from '../lhr-res-01';

export interface DaySimulation {
  /** Hourly solar output (kW), recorded on the sample day. */
  solar: number[];
  /** Hourly home usage (kW). */
  load: number[];
  /** Battery level at the end of each hour, in percent. */
  soc: number[];
  /** Hourly grid import (kW). */
  grid: number[];
  /** Hourly battery charge power (kW). */
  charge: number[];
}

const HOURS = 24;
const round = (value: number, digits: number) => Number(value.toFixed(digits));

/**
 * One deterministic 24-hour day: solar charges the battery first (capped by the charge limit),
 * the battery discharges only inside the evening peak and never below the outage reserve,
 * and the grid covers whatever is left.
 */
export function simulateDay(): DaySimulation {
  const { batteryCapacityKwh, reserveFloorKwh, maxChargeKw, maxDischargeKw, efficiency } =
    SAMPLE_SITE;
  const solar = [...HOURLY_SOLAR_KW];
  const load = [...SAMPLE_LOAD_KW];
  const out: DaySimulation = { solar, load, soc: [], grid: [], charge: [] };

  let stored = reserveFloorKwh;
  for (let hour = 0; hour < HOURS; hour++) {
    const net = (solar[hour] as number) - (load[hour] as number);
    const inPeak = hour >= SAMPLE_SITE.peakStartHour && hour < SAMPLE_SITE.peakEndHour;
    let grid = 0;
    let charge = 0;
    if (net > 0) {
      charge = Math.min(net, maxChargeKw, (batteryCapacityKwh - stored) / efficiency);
      stored += charge * efficiency;
    } else if (inPeak) {
      const discharge = Math.min(
        -net,
        maxDischargeKw,
        Math.max(0, stored - reserveFloorKwh) * efficiency,
      );
      stored -= discharge / efficiency;
      grid = -net - discharge;
    } else {
      grid = -net;
    }
    out.soc.push(round((stored / batteryCapacityKwh) * 100, 0));
    out.grid.push(round(grid, 2));
    out.charge.push(round(charge, 2));
  }
  return out;
}
