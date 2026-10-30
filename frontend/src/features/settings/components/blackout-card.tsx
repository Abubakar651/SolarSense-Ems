import { useState } from 'react';
import { FieldError } from '@/components/forms/field-error';
import { Icon } from '@/components/ui/icon';
import type { BlackoutWindow } from '@/types/domain/settings';
import { blackoutError, blackoutLength } from '../view-model';

interface BlackoutCardProps {
  blackouts: readonly BlackoutWindow[];
  onChange: (blackouts: BlackoutWindow[]) => void;
}

export function BlackoutCard({ blackouts, onChange }: BlackoutCardProps) {
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [error, setError] = useState('');

  const add = () => {
    const problem = blackoutError(start, end, blackouts);
    setError(problem ?? '');
    if (problem) return;
    onChange([...blackouts, { start, end }]);
    setStart('');
    setEnd('');
  };

  return (
    <div className="card">
      <h2 style={{ marginBottom: 4 }}>Known blackouts</h2>
      <p className="muted small" style={{ marginBottom: 'var(--sp-4)' }}>
        If you know when the power goes out every day, add it here.
      </p>
      {blackouts.length > 0 ? (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }} aria-label="Known blackouts">
          {blackouts.map(({ start: from, end: to }) => (
            <li className="setting" key={`${from}-${to}`}>
              <div>
                <div className="t num">{`${from} – ${to}`}</div>
                <p className="small muted">{`Every day, ${blackoutLength(from, to)}`}</p>
              </div>
              <button
                className="icon-btn"
                type="button"
                aria-label={`Remove blackout ${from} to ${to}`}
                onClick={() =>
                  onChange(blackouts.filter((entry) => entry.start !== from || entry.end !== to))
                }
              >
                <Icon name="trash" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted small">No blackouts added.</p>
      )}
      <div className="two" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="blackout-from">Blackout starts</label>
          <input
            className="input"
            id="blackout-from"
            type="time"
            value={start}
            aria-invalid={error ? true : undefined}
            aria-describedby="blackout-err"
            onChange={(event) => setStart(event.target.value)}
          />
        </div>
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="blackout-to">Ends</label>
          <input
            className="input"
            id="blackout-to"
            type="time"
            value={end}
            aria-invalid={error ? true : undefined}
            aria-describedby="blackout-err"
            onChange={(event) => setEnd(event.target.value)}
          />
        </div>
      </div>
      <FieldError id="blackout-err" message={error} />
      <button
        className="btn btn-secondary"
        type="button"
        style={{ marginTop: 'var(--sp-3)' }}
        onClick={add}
      >
        Add blackout
      </button>
    </div>
  );
}
