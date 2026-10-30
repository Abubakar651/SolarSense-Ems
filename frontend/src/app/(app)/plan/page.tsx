import type { Metadata } from 'next';
import { CardHeader } from '@/components/ui/card-header';
import { ChartTable } from '@/components/ui/data-table';
import { IconChip } from '@/components/ui/icon-chip';
import { KpiCard } from '@/components/ui/kpi-card';
import { PageHeader } from '@/components/ui/page-header';
import { PlanTimeline } from '@/features/plan/components/plan-timeline';
import { planSummary } from '@/features/plan/view-model';
import { getServices } from '@/services';

export const metadata: Metadata = { title: "Today's plan" };

const TABLE_COLUMNS = [
  { label: 'Hour' },
  { label: 'Solar kW', right: true },
  { label: 'Usage kW', right: true },
  { label: 'Battery %', right: true },
  { label: 'Grid kW', right: true },
];

export default async function PlanPage() {
  const plan = await getServices().energy.getDayPlan();
  const summary = planSummary(plan);

  return (
    <section data-route="plan">
      <PageHeader title="Today's plan">
        What the system expects and what it will do over the next 24 hours.
      </PageHeader>
      <div
        className="card"
        style={{
          marginBottom: 'var(--sp-4)',
          borderColor: 'var(--primary-line)',
          background: 'var(--primary-soft)',
        }}
      >
        <div className="row" style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
          <IconChip icon="check" tone="ok" style={{ background: '#fff' }} />
          <div>
            <h2 id="plan-ban-t">{summary.bannerTitle}</h2>
            <p className="muted" style={{ marginTop: 4 }} id="plan-ban-d">
              {summary.bannerDetail}
            </p>
          </div>
        </div>
      </div>
      <div className="card">
        <CardHeader
          title="24-hour timeline"
          subtitle="Hover, tap or use the arrow keys on the chart to inspect an hour."
        />
        <div className="legend" aria-hidden="true">
          <span>
            <i className="sw" />
            Solar (kW)
          </span>
          <span>
            <i className="sw" style={{ background: 'var(--c-solar)', opacity: 0.45 }} />
            Used directly
          </span>
          <span>
            <i className="sw line" />
            Usage (kW)
          </span>
          <span>
            <i className="sw ghost" />
            No sun
          </span>
          <span>
            <i className="sw hatch" />
            Peak hours
          </span>
        </div>
        <PlanTimeline plan={plan} />
        <ChartTable columns={TABLE_COLUMNS} rows={summary.tableRows} />
      </div>
      <div className="g-3 grid" style={{ marginTop: 'var(--sp-4)' }}>
        <KpiCard
          label="Expected solar today"
          value={
            <>
              <span id="pl-solar">{summary.solarKwh}</span>
              <small>kWh</small>
            </>
          }
          sub={summary.solarSub}
        />
        <KpiCard
          label="Expected usage today"
          value={
            <>
              <span id="pl-load">{summary.loadKwh}</span>
              <small>kWh</small>
            </>
          }
          sub={summary.loadSub}
        />
        <KpiCard
          label="Grid import expected"
          value={
            <>
              <span id="pl-grid">{summary.gridKwh}</span>
              <small>kWh</small>
            </>
          }
          sub={summary.gridSub}
        />
      </div>
    </section>
  );
}
