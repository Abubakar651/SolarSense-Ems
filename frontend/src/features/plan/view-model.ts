import { longDate } from '@/lib/dates';
import { pad } from '@/lib/format';
import type { DayPlan } from '@/types/domain/energy';

const sum = (values: number[]) => values.reduce((a, b) => a + b, 0);

export interface PlanSummary {
  bannerTitle: string;
  bannerDetail: string;
  solarKwh: string;
  solarSub: string;
  loadKwh: string;
  loadSub: string;
  gridKwh: string;
  gridSub: string;
  tableRows: string[][];
}

/** Tonight's peak-hour split and the day totals shown on the plan screen. */
export function planSummary(plan: DayPlan): PlanSummary {
  const peakHours = plan.load
    .map((_, hour) => hour)
    .filter((hour) => hour >= plan.peakStartHour && hour < plan.peakEndHour);
  const peakLoad = sum(peakHours.map((hour) => plan.load[hour] as number));
  const peakGrid = sum(peakHours.map((hour) => plan.grid[hour] as number));
  const reservePct = Math.round((plan.reserveFloorKwh / plan.batteryCapacityKwh) * 100);
  const gridKwh = sum(plan.grid);
  const offPeakGridKwh = gridKwh - peakGrid;

  return {
    bannerTitle: `Tonight, the battery covers ${Math.round((1 - peakGrid / peakLoad) * 100)}% of your peak-hour usage`,
    bannerDetail:
      `From ${pad(plan.peakStartHour)}:00 to ${pad(plan.peakEndHour)}:00 your home uses ${peakLoad.toFixed(1)} kWh. ` +
      `The battery supplies ${(peakLoad - peakGrid).toFixed(1)} kWh and the grid the remaining ${peakGrid.toFixed(1)} kWh. ` +
      `The last ${reservePct}% of the battery is kept back for outages, and it is never charged from the grid at peak rates.`,
    solarKwh: sum(plan.solar).toFixed(1),
    solarSub: `Recorded output on ${longDate(plan.sampleDate)}`,
    loadKwh: sum(plan.load).toFixed(1),
    loadSub: `Highest use around ${pad(plan.load.indexOf(Math.max(...plan.load)))}:00`,
    gridKwh: gridKwh.toFixed(1),
    gridSub:
      gridKwh === 0
        ? 'No grid power needed'
        : `${Math.round((offPeakGridKwh / gridKwh) * 100)}% of it at the cheap rate`,
    tableRows: plan.solar.map((solar, hour) => [
      `${pad(hour)}:00`,
      solar.toFixed(1),
      (plan.load[hour] as number).toFixed(1),
      String(plan.soc[hour]),
      (plan.grid[hour] as number).toFixed(1),
    ]),
  };
}
