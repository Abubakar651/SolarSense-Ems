import { Fragment } from 'react';
import type { ReviewRow } from '../view-model';

export function StepReview({ hidden, rows }: { hidden: boolean; rows: ReviewRow[] }) {
  return (
    <div className="card" data-step="3" hidden={hidden}>
      <h2 style={{ marginBottom: 'var(--sp-4)' }}>Review &amp; finish</h2>
      <dl
        id="onb-review"
        style={{ margin: 0, display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '8px 16px' }}
      >
        {rows.map(({ label, value }) => (
          <Fragment key={label}>
            <dt className="muted">{label}</dt>
            <dd style={{ margin: 0, fontWeight: 500 }}>{value}</dd>
          </Fragment>
        ))}
      </dl>
      <p className="muted small" style={{ marginTop: 'var(--sp-4)' }}>
        After finishing we&apos;ll connect to your inverter and build your first 24-hour plan.
      </p>
    </div>
  );
}
