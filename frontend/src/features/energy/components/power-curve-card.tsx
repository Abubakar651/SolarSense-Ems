import Link from 'next/link';
import { PowerCurveChart } from '@/components/charts/power-curve-chart';
import { CardHeader } from '@/components/ui/card-header';
import { Icon } from '@/components/ui/icon';
import { longDate } from '@/lib/dates';
import type { DayCurve } from '@/types/domain/energy';
import { CURVE_COLORS, neighbourDays } from '../curve';

const kw = (value: number | null) => (value === null ? '—' : `${value.toFixed(2)} kW`);

function DayLink({ date, label, flip }: { date: string | null; label: string; flip?: boolean }) {
  const arrow = <Icon name="arrow" style={flip ? { transform: 'rotate(180deg)' } : undefined} />;
  if (date === null) {
    return (
      <span className="btn btn-ghost btn-sm" aria-disabled="true" aria-label={label}>
        {arrow}
      </span>
    );
  }
  return (
    <Link className="btn btn-ghost btn-sm" href={`/energy?date=${date}`} aria-label={label}>
      {arrow}
    </Link>
  );
}

/** One day's PV, home, battery and grid power with its peaks, and links to the days either side. */
export function PowerCurveCard({ curve }: { curve: DayCurve }) {
  const { previous, next } = neighbourDays(curve.dates, curve.date);
  const { peaks } = curve;
  const tiles: [string, string][] = [
    ['Peak solar', kw(peaks.pvKw)],
    ['Peak home use', kw(peaks.loadKw)],
    ['Peak charge / discharge', `${kw(peaks.chargeKw)} / ${kw(peaks.dischargeKw)}`],
    ['Peak import / export', `${kw(peaks.importKw)} / ${kw(peaks.exportKw)}`],
  ];

  return (
    <div className="card">
      <CardHeader
        title="Power curve"
        action={
          <div className="row">
            <DayLink date={previous} label="Previous day" flip />
            <b className="num" aria-live="polite">
              {longDate(curve.date)}
            </b>
            <DayLink date={next} label="Next day" />
          </div>
        }
      />
      {curve.intervalMinutes === 60 && (
        <p className="small muted">
          <span className="badge b-neutral">Hourly averages</span>
        </p>
      )}
      <dl className="e-tiles">
        {tiles.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className="num">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="legend" aria-hidden="true">
        <span>
          <i className="sw" style={{ background: CURVE_COLORS.pv }} />
          Solar
        </span>
        <span>
          <i className="sw" style={{ background: CURVE_COLORS.load }} />
          Home
        </span>
        <span>
          <i className="sw" style={{ background: CURVE_COLORS.battery }} />
          Battery (+ charging)
        </span>
        <span>
          <i className="sw" style={{ background: CURVE_COLORS.grid }} />
          Grid (+ exporting)
        </span>
      </div>
      <PowerCurveChart
        id="chart-curve"
        points={curve.points}
        ariaLabel={`Power through ${longDate(curve.date)}. Solar peaks at ${kw(peaks.pvKw)} and home use at ${kw(peaks.loadKw)}.`}
      />
    </div>
  );
}
