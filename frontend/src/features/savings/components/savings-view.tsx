'use client';

import { useState } from 'react';
import { BarChart } from '@/components/charts/bar-chart';
import { CardHeader } from '@/components/ui/card-header';
import { CollectingBadge } from '@/features/history/components/collecting-badge';
import { FreshnessBadge } from '@/features/history/components/freshness-badge';
import { ChartTable } from '@/components/ui/data-table';
import { KpiCard, KpiStrip } from '@/components/ui/kpi-card';
import { PageHeader } from '@/components/ui/page-header';
import { Seg } from '@/components/ui/seg';
import { fmt } from '@/lib/format';
import type { Freshness, HistoryNotReady } from '@/types/domain/history';
import type { SavingsData, SavingsRange } from '@/types/domain/savings';
import { savingsSummary } from '../view-model';

const RANGES = [
  { value: 'week', label: '7 days' },
  { value: 'month', label: '30 days' },
  { value: 'year', label: '12 months' },
] as const;

interface SavingsViewProps {
  data: SavingsData;
  freshness?: Freshness;
  /** Set while the data above is a zeroed placeholder, so the header shows a collecting badge instead. */
  notReady?: HistoryNotReady;
}

export function SavingsView({ data, freshness, notReady }: SavingsViewProps) {
  const [range, setRange] = useState<SavingsRange>('month');
  const series = data[range];
  const summary = savingsSummary(series);

  return (
    <section data-route="savings">
      <PageHeader
        title="Savings"
        actions={
          <Seg
            options={RANGES}
            value={range}
            onChange={setRange}
            ariaLabel="Time range"
            id="savRange"
          />
        }
      >
        {notReady ? <CollectingBadge result={notReady} /> : <FreshnessBadge freshness={freshness as Freshness} />}
      </PageHeader>
      <KpiStrip>
        <KpiCard
          label="Total saved"
          value={summary.total}
          sub={summary.average}
          subId="sv-total-sub"
        />
        <KpiCard
          label={`Grid bill, ${data.currentMonth.label}`}
          value={`PKR ${fmt(data.currentMonth.costPkr)}`}
          sub={`vs PKR ${fmt(data.currentMonth.withoutSolarPkr)} without solar`}
        />
        <KpiCard
          label="Export credit earned"
          value={summary.exportCredit}
          sub={`At PKR ${data.exportRatePkr}/kWh`}
        />
        <KpiCard
          label="Self-powered"
          value={
            <>
              {data.currentMonth.selfPoweredPct}
              <small>%</small>
            </>
          }
          sub={data.currentMonth.label}
        />
      </KpiStrip>
      <div className="g-21 grid" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="card">
          <div className="card-h">
            <div>
              <h2 id="sv-title">{series.title}</h2>
            </div>
          </div>
          <BarChart
            id="chart-sav"
            values={series.values}
            labels={series.labels}
            height={240}
            labelEvery={(width) => (range === 'month' ? (width < 500 ? 5 : 2) : 1)}
            showValues={range !== 'month'}
            tipName="Saved"
            tipFormat={(v) => `PKR ${fmt(v)}`}
            tipHead={(label) => (range === 'month' ? `Day ${label}` : label)}
            ariaLabel={`Bar chart of ${series.title.toLowerCase()} in rupees over the selected range.`}
          />
          <ChartTable
            columns={[{ label: summary.periodLabel }, { label: 'Saved (PKR)', right: true }]}
            rows={summary.tableRows}
          />
        </div>
        <div className="card">
          <CardHeader title="Where savings come from" />
          <div className="stack" id="sav-break">
            {summary.breakdown.map(({ label, amount, widthPct }) => (
              <div key={label}>
                <div className="row between small">
                  <span>{label}</span>
                  <b className="num">{amount}</b>
                </div>
                <div className="bar" style={{ marginTop: 6 }}>
                  <i style={{ width: `${widthPct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
