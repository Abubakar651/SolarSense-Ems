'use client';

import { useState } from 'react';
import { GroupedBarChart } from '@/components/charts/grouped-bar-chart';
import { CardHeader } from '@/components/ui/card-header';
import { ChartTable } from '@/components/ui/data-table';
import { Seg } from '@/components/ui/seg';
import type { EnergyHistory } from '@/types/domain/energy';
import { energyRange, type EnergyRange } from '../monitoring';

const RANGES = [
  { value: 'week', label: '7 days' },
  { value: 'month', label: '30 days' },
  { value: 'year', label: '12 months' },
] as const;

const SERIES_STYLE = [
  { name: 'Generation', color: 'var(--accent)' },
  { name: 'Usage', color: 'var(--primary)' },
  { name: 'Imported', color: 'var(--muted)' },
  { name: 'Exported', color: 'var(--tint-3)' },
] as const;

const kwh = (value: number) => `${value.toFixed(1)} kWh`;
const axis = (value: number) => (value >= 1000 ? `${value / 1000}k` : String(value));

/** Daily or monthly generation, usage, import and export as grouped bars, with the range's totals. */
export function EnergyMonitoringCard({ history }: { history: EnergyHistory }) {
  const [range, setRange] = useState<EnergyRange>('week');
  const { series, totals } = energyRange(history, range);
  const values = [series.generation, series.consumption, series.imported, series.exported];
  const tiles: [string, string][] = [
    ['Generated', kwh(totals.generationKwh)],
    ['Used', kwh(totals.consumptionKwh)],
    ['Imported', kwh(totals.importKwh)],
    ['Exported', kwh(totals.exportKwh)],
    ['Self-consumed', kwh(totals.selfConsumedKwh)],
  ];
  if (totals.batteryChargedKwh !== null) tiles.push(['Charged', kwh(totals.batteryChargedKwh)]);
  if (totals.batteryDischargedKwh !== null) {
    tiles.push(['Discharged', kwh(totals.batteryDischargedKwh)]);
  }

  return (
    <div className="card">
      <CardHeader
        title="Energy monitoring"
        action={
          <Seg
            options={RANGES}
            value={range}
            onChange={setRange}
            ariaLabel="Energy range"
            id="energyRange"
          />
        }
      />
      <dl className="e-tiles">
        {tiles.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className="num">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="legend" aria-hidden="true">
        {SERIES_STYLE.map(({ name, color }) => (
          <span key={name}>
            <i className="sw" style={{ background: color }} />
            {name}
          </span>
        ))}
      </div>
      <GroupedBarChart
        id="chart-energy"
        labels={series.labels}
        yFormat={axis}
        labelEvery={(width) =>
          range === 'month' ? (width < 500 ? 5 : 2) : range === 'year' && width < 500 ? 2 : 1
        }
        tipHead={(label) => (range === 'month' ? `Day ${label}` : label)}
        ariaLabel="Grouped bar chart of energy generated, used, imported and exported over the selected range, in kWh."
        series={SERIES_STYLE.map((style, i) => ({ ...style, values: values[i] as number[] }))}
      />
      <ChartTable
        columns={[
          { label: range === 'year' ? 'Month' : 'Day' },
          { label: 'Generated', right: true },
          { label: 'Used', right: true },
          { label: 'Imported', right: true },
          { label: 'Exported', right: true },
        ]}
        rows={series.labels.map((label, i) => [
          label,
          ...values.map((column) => (column[i] as number).toFixed(1)),
        ])}
      />
    </div>
  );
}
