import type { CurvePoint, DayCurve, DayPeaks, DayPlan } from '@/types/domain/energy';

/** GET /api/insights/day-curve. Battery is + while charging, grid is + while exporting. */
export interface DayCurveDto {
  /** Null while the site has no data at all. */
  date: string | null;
  interval_minutes: number | null;
  points: {
    time: string;
    pv_kw: number;
    load_kw: number;
    battery_kw: number | null;
    grid_kw: number | null;
    soc_pct: number | null;
  }[];
  peaks: {
    pv_kw: number | null;
    load_kw: number | null;
    charge_kw: number | null;
    discharge_kw: number | null;
    import_kw: number | null;
    export_kw: number | null;
  };
  dates: string[];
}

const highest = (values: number[]): number | null => (values.length ? Math.max(...values) : null);
const present = (values: (number | null)[]): number[] =>
  values.filter((value): value is number => value !== null);

/** The day's highest readings. Battery and grid are signed, so each direction is its own peak. */
export function peaksOf(points: readonly CurvePoint[]): DayPeaks {
  const battery = present(points.map((p) => p.batteryKw));
  const grid = present(points.map((p) => p.gridKw));
  return {
    pvKw: highest(points.map((p) => p.pvKw)),
    loadKw: highest(points.map((p) => p.loadKw)),
    chargeKw: battery.length ? highest(battery.filter((kw) => kw > 0)) : null,
    dischargeKw: battery.length ? highest(battery.filter((kw) => kw < 0).map((kw) => -kw)) : null,
    importKw: grid.length ? highest(grid.filter((kw) => kw < 0).map((kw) => -kw)) : null,
    exportKw: grid.length ? highest(grid.filter((kw) => kw > 0)) : null,
  };
}

/** The API's curve for one day, or null while the site has no data. */
export function toDayCurve(dto: DayCurveDto): DayCurve | null {
  if (dto.date === null || dto.interval_minutes === null) return null;
  return {
    date: dto.date,
    intervalMinutes: dto.interval_minutes,
    points: dto.points.map((p) => ({
      time: p.time,
      pvKw: p.pv_kw,
      loadKw: p.load_kw,
      batteryKw: p.battery_kw,
      gridKw: p.grid_kw,
      socPct: p.soc_pct,
    })),
    peaks: {
      pvKw: dto.peaks.pv_kw,
      loadKw: dto.peaks.load_kw,
      chargeKw: dto.peaks.charge_kw,
      dischargeKw: dto.peaks.discharge_kw,
      importKw: dto.peaks.import_kw,
      exportKw: dto.peaks.export_kw,
    },
    dates: dto.dates,
  };
}

/**
 * The sample day's plan as an hourly curve. The plan only has charge power, so the battery's power is
 * what its level changed by over the hour (kWh in an hour is kW); the first hour has no earlier level.
 */
export function curveFromPlan(plan: DayPlan): DayCurve {
  const points: CurvePoint[] = plan.solar.map((pvKw, hour) => {
    const change = hour === 0 ? 0 : (plan.soc[hour] as number) - (plan.soc[hour - 1] as number);
    return {
      time: `${String(hour).padStart(2, '0')}:00`,
      pvKw,
      loadKw: plan.load[hour] as number,
      batteryKw: (change / 100) * plan.batteryCapacityKwh + 0,
      gridKw:
        -(plan.grid[hour] as number) +
        Math.max(0, pvKw - (plan.load[hour] as number) - (plan.charge[hour] as number)),
      socPct: plan.soc[hour] as number,
    };
  });
  return {
    date: plan.sampleDate,
    intervalMinutes: 60,
    points,
    peaks: peaksOf(points),
    dates: [plan.sampleDate],
  };
}
