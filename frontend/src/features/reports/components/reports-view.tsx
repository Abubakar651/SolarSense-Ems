'use client';

import { useState } from 'react';
import { BarChart } from '@/components/charts/bar-chart';
import { DataTable } from '@/components/ui/data-table';
import { Icon } from '@/components/ui/icon';
import { PageHeader } from '@/components/ui/page-header';
import { fmt } from '@/lib/format';
import { useToast } from '@/providers/toast-provider';
import type { MonthReport, ReportData } from '@/types/domain/reports';
import { EmailReportsCard } from './email-reports-card';

const TOTAL_STYLE = { fontSize: '1.375rem' } as const;

interface ReportsViewProps {
  report: ReportData;
}

export function ReportsView({ report }: ReportsViewProps) {
  const toast = useToast();
  const [monthName, setMonthName] = useState((report.months[0] as MonthReport).name);
  const month = report.months.find(({ name }) => name === monthName) as MonthReport;

  return (
    <section data-route="reports">
      <PageHeader
        title="Reports"
        actions={
          <div className="row">
            <label className="sr-only" htmlFor="repMonth">
              Month
            </label>
            <select
              className="input"
              id="repMonth"
              style={{ width: 'auto' }}
              value={monthName}
              onChange={(event) => setMonthName(event.target.value)}
            >
              {report.months.map(({ name }) => (
                <option key={name}>{name}</option>
              ))}
            </select>
            {(['CSV', 'PDF'] as const).map((kind) => (
              <button
                key={kind}
                className={`btn ${kind === 'CSV' ? 'btn-secondary' : 'btn-primary'} export`}
                type="button"
                onClick={() => toast(`${kind} export is not available yet.`)}
              >
                <Icon name="download" />
                {kind}
              </button>
            ))}
          </div>
        }
      >
        Monthly summaries you can download or send to someone.
      </PageHeader>
      <div className="g-21 grid">
        <div className="report-sheet">
          <div className="row between" style={{ marginBottom: 'var(--sp-4)' }}>
            <div>
              <h2 id="rep-title">{`${month.name} summary`}</h2>
              <p className="muted small">{`${report.site} · ${month.coverage}`}</p>
            </div>
            <span className="badge b-warn">Sample data</span>
          </div>
          <div className="g-kpi grid" style={{ marginBottom: 'var(--sp-4)' }}>
            {month.totals.map(({ label, value }) => (
              <div key={label}>
                <div className="muted small">{label}</div>
                <b className="num" style={TOTAL_STYLE}>
                  {value}
                </b>
              </div>
            ))}
          </div>
          <h3 style={{ marginBottom: 8 }}>Daily savings (PKR)</h3>
          <BarChart
            id="chart-rep"
            values={month.dailyValues}
            labels={month.dailyLabels}
            height={180}
            labelEvery={(width) => (width < 500 ? 5 : 2)}
            tipName="Saved"
            tipFormat={(v) => `PKR ${fmt(v)}`}
            tipHead={(label) => `Day ${label}`}
            ariaLabel="Bar chart of daily savings for the selected month."
          />
          <h3 style={{ margin: 'var(--sp-5) 0 8px' }}>By week</h3>
          <p className="muted small" style={{ marginBottom: 8 }}>
            Daily and weekly figures are rebuilt from hourly data that ends on Oct 7, 2026, so they
            differ slightly from the metered monthly totals.
          </p>
          <DataTable
            columns={[
              { label: 'Week' },
              { label: 'Solar (kWh)', right: true },
              { label: 'Grid (kWh)', right: true },
              { label: 'Saved (PKR)', right: true },
            ]}
            rows={month.weeks.map((w) => [w.week, w.solarKwh, w.gridKwh, w.savedPkr])}
          />
        </div>
        <EmailReportsCard />
      </div>
    </section>
  );
}
