import type { ReactNode } from 'react';

export interface DonutSegment {
  label: string;
  value: number;
  /** Any CSS colour, usually a token such as var(--accent). */
  color: string;
}

interface DonutProps {
  segments: DonutSegment[];
  /** Big text in the hole, e.g. "62%". */
  center: ReactNode;
  centerLabel: string;
  ariaLabel: string;
  /** Formats a segment's value in the legend. */
  format: (value: number) => string;
}

const RADIUS = 42;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Ring chart of a few parts of a whole, with a legend of values and shares. */
export function Donut({ segments, center, centerLabel, ariaLabel, format }: DonutProps) {
  const total = segments.reduce((sum, { value }) => sum + Math.max(0, value), 0);
  let offset = 0;

  return (
    <figure className="donut">
      <div className="donut-ring">
        <svg viewBox="0 0 100 100" role="img" aria-label={ariaLabel}>
          <circle className="donut-track" cx="50" cy="50" r={RADIUS} />
          {total > 0 &&
            segments.map(({ label, value, color }) => {
              const length = (Math.max(0, value) / total) * CIRCUMFERENCE;
              const arc = (
                <circle
                  key={label}
                  cx="50"
                  cy="50"
                  r={RADIUS}
                  stroke={color}
                  strokeDasharray={`${length} ${CIRCUMFERENCE - length}`}
                  strokeDashoffset={-offset}
                />
              );
              offset += length;
              return arc;
            })}
        </svg>
        <div className="donut-center" aria-hidden="true">
          <b className="num">{center}</b>
          <span>{centerLabel}</span>
        </div>
      </div>
      <figcaption>
        <ul className="donut-legend">
          {segments.map(({ label, value, color }) => (
            <li key={label}>
              <i style={{ background: color }} />
              <span>{label}</span>
              <b className="num">{format(value)}</b>
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}
