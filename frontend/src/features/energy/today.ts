import type { DayPlan } from '@/types/domain/energy';
import type { InverterLive } from '@/types/domain/inverter';

/** A day's energy totals in kWh, and where they come from. */
export interface TodayEnergy {
  /** measured: the inverter's counters so far today; recorded: a replayed sample day; forecast: today's plan. */
  basis: 'measured' | 'recorded' | 'forecast';
  generationKwh: number;
  consumptionKwh: number;
  importKwh: number;
  exportKwh: number;
  /** Null when the source has no battery counters (the plan). */
  battery: { chargedKwh: number; dischargedKwh: number } | null;
}

export const BASIS_LABEL: Record<TodayEnergy['basis'], string> = {
  measured: 'So far today',
  recorded: 'Recorded day',
  forecast: 'Forecast',
};

/** The inverter's day counters; a sample reading's counters are for the recorded day. */
export function todayFromReading(data: InverterLive, isSample: boolean): TodayEnergy {
  return {
    basis: isSample ? 'recorded' : 'measured',
    generationKwh: data.todayPvKwh,
    consumptionKwh: data.todayLoadKwh,
    importKwh: data.todayImportKwh,
    exportKwh: data.todayExportKwh,
    battery: {
      chargedKwh: data.todayBatteryChargeKwh,
      dischargedKwh: data.todayBatteryDischargeKwh,
    },
  };
}

const sum = (values: number[]) => values.reduce((a, b) => a + b, 0);

/** Hourly kW averages sum to kWh. Export is the solar left after the home and the battery, as on the dashboard. */
export function todayFromPlan(plan: DayPlan): TodayEnergy {
  const exported = plan.solar.map((solar, hour) =>
    Math.max(0, solar - (plan.load[hour] as number) - (plan.charge[hour] as number)),
  );
  return {
    basis: plan.isSample ? 'recorded' : 'forecast',
    generationKwh: sum(plan.solar),
    consumptionKwh: sum(plan.load),
    importKwh: sum(plan.grid),
    exportKwh: sum(exported),
    battery: null,
  };
}

/** Two parts of a whole, with the first part's share in percent (0 when the whole is 0). */
export interface Split {
  firstKwh: number;
  secondKwh: number;
  firstPct: number;
}

function split(whole: number, second: number): Split {
  const secondKwh = Math.min(Math.max(0, second), Math.max(0, whole));
  const firstKwh = Math.max(0, whole - secondKwh);
  return { firstKwh, secondKwh, firstPct: whole > 0 ? Math.round((firstKwh / whole) * 100) : 0 };
}

/** Generation split into what the site used itself and what it exported. */
export const generationSplit = (today: TodayEnergy): Split =>
  split(today.generationKwh, today.exportKwh);

/** Consumption split into what solar and the battery covered and what was bought from the grid. */
export const consumptionSplit = (today: TodayEnergy): Split =>
  split(today.consumptionKwh, today.importKwh);
