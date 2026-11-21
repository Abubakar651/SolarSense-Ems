import { CardHeader } from '@/components/ui/card-header';
import { DataTable } from '@/components/ui/data-table';
import { KpiCard } from '@/components/ui/kpi-card';
import { longDate } from '@/lib/dates';
import type { AdvisoryResult } from '@/types/domain/advisory';
import { briefStats, generationModeLabel, metricRows } from '../view-model';

/** The written daily brief. The text comes from the backend (or the sample builder); this only lays it out. */
export function AdvisoryCard({ result }: { result: AdvisoryResult }) {
  if (result.status === 'unavailable') {
    return (
      <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
        <CardHeader title="Daily brief" />
        <p className="small muted" id="adv-unavailable">
          Today’s brief isn’t available right now: the weather forecast it is written from couldn’t
          be fetched. It comes back as soon as the forecast does.
        </p>
      </div>
    );
  }

  const { advisory } = result;
  const stats = briefStats(advisory);
  return (
    <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
      <CardHeader
        title="Daily brief"
        subtitle={longDate(advisory.date)}
        action={
          advisory.isSample ? <span className="badge b-neutral">Sample brief</span> : undefined
        }
      />
      <h3 id="adv-headline">{advisory.headline}</h3>
      <div className="g-3 grid" style={{ marginTop: 'var(--sp-3)' }}>
        {stats.map(({ title, icon, value, unit, sub }) => (
          <KpiCard
            key={title}
            icon={icon}
            label={title}
            value={
              <>
                {value}
                {unit && <small>{unit}</small>}
              </>
            }
            sub={sub}
          />
        ))}
      </div>
      <h3 style={{ margin: 'var(--sp-4) 0 var(--sp-2)' }}>What to do</h3>
      <ul className="small" style={{ paddingLeft: 'var(--sp-4)' }}>
        {advisory.recommendedActions.map((action) => (
          <li key={action}>{action}</li>
        ))}
      </ul>
      <details className="alt">
        <summary>Figures behind the brief</summary>
        <DataTable
          columns={[{ label: 'Figure' }, { label: 'Value', right: true }]}
          rows={metricRows(advisory.keyMetrics)}
        />
      </details>
      <p className="xs faint" style={{ marginTop: 'var(--sp-2)' }}>
        {`Written by: ${generationModeLabel(advisory.generationMode)}`}
      </p>
    </div>
  );
}
