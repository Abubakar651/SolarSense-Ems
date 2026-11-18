import { CardHeader } from '@/components/ui/card-header';
import { DataTable } from '@/components/ui/data-table';
import { longDate } from '@/lib/dates';
import type { Advisory } from '@/types/domain/advisory';
import { generationModeLabel, metricRows } from '../view-model';

const BRIEFS = [
  { title: 'Peak-hour savings', key: 'dispatchArbitrageBrief' },
  { title: 'Outage backup', key: 'blackoutResilienceBrief' },
  { title: 'Panel cleaning', key: 'soilingMaintenanceBrief' },
] as const;

/** The written daily brief. The text comes from the backend (or the sample builder); this only lays it out. */
export function AdvisoryCard({ advisory }: { advisory: Advisory }) {
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
        {BRIEFS.map(({ title, key }) => (
          <div key={key}>
            <div className="t">{title}</div>
            <p className="small muted">{advisory[key]}</p>
          </div>
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
