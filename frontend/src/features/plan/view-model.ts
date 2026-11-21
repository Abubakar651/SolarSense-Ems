import type { IconName } from '@/components/ui/icon-paths';
import { longDate } from '@/lib/dates';
import { pad } from '@/lib/format';
import type { Advisory, AdvisoryMetrics } from '@/types/domain/advisory';
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

  const batteryCoverPct = peakLoad === 0 ? 0 : Math.round((1 - peakGrid / peakLoad) * 100);

  return {
    bannerTitle: `Tonight, the battery covers ${batteryCoverPct}% of your peak-hour usage`,
    bannerDetail:
      `${pad(plan.peakStartHour)}:00–${pad(plan.peakEndHour)}:00 · ${peakLoad.toFixed(1)} kWh used: ` +
      `battery ${(peakLoad - peakGrid).toFixed(1)}, grid ${peakGrid.toFixed(1)} · ${reservePct}% kept for outages`,
    solarKwh: sum(plan.solar).toFixed(1),
    solarSub: plan.isSample
      ? `Recorded output on ${longDate(plan.sampleDate)}`
      : `Forecast for ${longDate(plan.sampleDate)}`,
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

const METRIC_ROWS: { label: string; key: keyof AdvisoryMetrics; unit: string; digits: number }[] = [
  { label: 'Solar generated', key: 'solarGenerationKwh', unit: 'kWh', digits: 1 },
  { label: 'Home usage', key: 'householdLoadKwh', unit: 'kWh', digits: 1 },
  { label: 'Bought from the grid', key: 'gridImportKwh', unit: 'kWh', digits: 1 },
  { label: 'Sent to the grid', key: 'netMeteringExportKwh', unit: 'kWh', digits: 1 },
  { label: 'Export credit', key: 'exportRevenuePkr', unit: 'PKR', digits: 0 },
  { label: 'Battery used at peak', key: 'peakBatteryDischargeKwh', unit: 'kWh', digits: 1 },
  { label: 'Outage time', key: 'outageHours', unit: 'h', digits: 2 },
  { label: 'Saved by the plan', key: 'netSavingsPkr', unit: 'PKR', digits: 0 },
  { label: 'Dust loss', key: 'soilingLossKwh', unit: 'kWh', digits: 1 },
  { label: 'Gain from washing', key: 'netCleaningBenefitPkr', unit: 'PKR', digits: 0 },
];

/** Label and value for each advisory figure; a figure the plan could not work out shows a dash. */
export function metricRows(metrics: AdvisoryMetrics): string[][] {
  return METRIC_ROWS.map(({ label, key, unit, digits }) => {
    const value = metrics[key];
    if (value === null) return [label, '—'];
    const text = digits === 0 ? Math.round(value).toLocaleString('en-US') : value.toFixed(digits);
    return [label, `${text} ${unit}`];
  });
}

export interface BriefStat {
  title: string;
  icon: IconName;
  value: string;
  unit?: string;
  sub: string;
}

/** The three daily-brief figures as stat cards: one headline number each, no prose. */
export function briefStats(advisory: Advisory): BriefStat[] {
  const m = advisory.keyMetrics;
  const batteryShare =
    m.householdLoadKwh === 0
      ? 0
      : Math.round((m.peakBatteryDischargeKwh / m.householdLoadKwh) * 100);

  return [
    {
      title: 'Peak-hour savings',
      icon: 'zap',
      value: m.netSavingsPkr === null ? '—' : Math.round(m.netSavingsPkr).toLocaleString('en-US'),
      unit: m.netSavingsPkr === null ? undefined : 'PKR',
      sub: `Battery covers ${batteryShare}% of peak usage`,
    },
    {
      title: 'Outage backup',
      icon: 'shield',
      value: m.outageHours.toFixed(m.outageHours === 0 ? 0 : 1),
      unit: 'h logged today',
      sub: m.outageHours === 0 ? 'No blackouts today' : 'Blackout time today',
    },
    {
      title: 'Panel cleaning',
      icon: 'camera',
      value: m.soilingLossKwh === null ? '—' : m.soilingLossKwh.toFixed(1),
      unit: m.soilingLossKwh === null ? undefined : 'kWh lost to dust',
      sub:
        m.netCleaningBenefitPkr === null
          ? 'Dust estimate still collecting'
          : `Washing would gain ${Math.round(m.netCleaningBenefitPkr).toLocaleString('en-US')} PKR`,
    },
  ];
}

/** "sample_from_recorded_day" -> "Sample from recorded day". */
export function generationModeLabel(mode: string): string {
  const words = mode.replace(/_/g, ' ');
  return words.charAt(0).toUpperCase() + words.slice(1);
}
