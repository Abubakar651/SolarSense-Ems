import type { Metadata } from 'next';
import { CardHeader } from '@/components/ui/card-header';
import { ChartTable } from '@/components/ui/data-table';
import { IconChip } from '@/components/ui/icon-chip';
import { KpiCard } from '@/components/ui/kpi-card';
import { PageHeader } from '@/components/ui/page-header';
import { AdvisoryCard } from '@/features/plan/components/advisory-card';
import { CollectingBadge } from '@/features/history/components/collecting-badge';
import { PlanTimeline } from '@/features/plan/components/plan-timeline';
import { forecastNote, zeroDayPlan } from '@/features/dashboard/view-model';
import { planSummary } from '@/features/plan/view-model';
import { getServices } from '@/services';

export const metadata: Metadata = { title: "Today's plan" };

const PLAN_UNAVAILABLE_MESSAGE =
  "Today's plan isn't available right now: the weather forecast it is made from couldn't be fetched.";

const TABLE_COLUMNS = [
  { label: 'Hour' },
  { label: 'Solar kW', right: true },
  { label: 'Usage kW', right: true },
  { label: 'Battery %', right: true },
  { label: 'Grid kW', right: true },
];

export default async function PlanPage() {
  const services = getServices();
  const [planResult, advisory] = await Promise.all([
    services.energy.getDayPlan(),
    services.advisory.getAdvisory(),
  ]);
  const ready = planResult.status === 'ready';
  const plan = ready ? planResult.plan : zeroDayPlan();
  const summary = planSummary(plan);
  const note = forecastNote(plan);

  return (
    <section data-route="plan">
      <PageHeader title="Today's plan">
        {!ready && (
          <CollectingBadge
            result={{ status: planResult.status, loggedDays: 0 }}
            unavailableMessage={PLAN_UNAVAILABLE_MESSAGE}
          />
        )}
      </PageHeader>
      <div className="card">
        <div
          className="row"
          style={{ alignItems: 'flex-start', flexWrap: 'nowrap', marginBottom: 'var(--sp-3)' }}
        >
          <IconChip icon="check" tone="ok" />
          <div>
            <h2 id="plan-ban-t">{summary.bannerTitle}</h2>
            <p className="muted" style={{ marginTop: 4 }} id="plan-ban-d">
              {summary.bannerDetail}
            </p>
          </div>
        </div>
        <CardHeader title="24-hour timeline" />
        <div className="legend" aria-hidden="true">
          <span title="Solar (kW)">
            <i className="sw" />
            Solar
          </span>
          <span title="Used directly">
            <i className="sw" style={{ background: 'var(--c-solar)', opacity: 0.45 }} />
            Used
          </span>
          <span title="Usage (kW)">
            <i className="sw line" />
            Usage
          </span>
          <span title="No sun">
            <i className="sw ghost" />
            No sun
          </span>
          <span title="Peak hours">
            <i className="sw hatch" />
            Peak
          </span>
        </div>
        <PlanTimeline plan={plan} />
        {note && (
          <p className="small muted" id="plan-forecast-note">
            {note}
          </p>
        )}
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
      <AdvisoryCard result={advisory} />
    </section>
  );
}
