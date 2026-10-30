import { memo } from 'react';
import type { PlanLayout } from '@/lib/charts/plan-layout';
import { smooth, smoothArea, type Point } from '@/lib/charts/smooth';
import { pad } from '@/lib/format';
import { FadeGradient } from './gradient';

export interface PlanSeries {
  solar: number[];
  load: number[];
  soc: number[];
  peakStartHour: number;
  peakEndHour: number;
}

interface StaticProps {
  id: string;
  w: number;
  h: number;
  layout: PlanLayout;
  series: PlanSeries;
  /** Hidden when it would collide with the "Now" label. */
  showPeakLabel: boolean;
}

/**
 * Everything in the plan chart that does not depend on the clock or the pointer. Memoised so the
 * live "Now" marker can move without re-rendering (or re-creating) the plotted curves.
 */
export const PlanChartStatic = memo(function PlanChartStatic({
  id,
  w,
  h,
  layout,
  series,
  showPeakLabel,
}: StaticProps) {
  const { m, iw, batteryTop, batteryBottom, x, hourEdge, ySolar, yBattery, tickEvery } = layout;
  const { solar, load, soc, peakStartHour, peakEndHour } = series;
  const solarPoints: Point[] = solar.map((v, i) => [x(i), ySolar(v)]);
  const loadPoints: Point[] = load.map((v, i) => [x(i), ySolar(v)]);
  const batteryPoints: Point[] = soc.map((v, i) => [x(i), yBattery(v)]);
  const peakIndex = solar.indexOf(Math.max(...solar));
  const peakKw = solar[peakIndex] as number;
  const ticks = Array.from({ length: Math.ceil(24 / tickEvery) }, (_, k) => k * tickEvery);

  return (
    <>
      <defs>
        <FadeGradient id={`${id}-gs`} color="var(--c-solar)" />
        <FadeGradient id={`${id}-gb`} />
        <clipPath id={`${id}-cu`}>
          <path d={smoothArea(loadPoints, ySolar(0))} />
        </clipPath>
      </defs>
      <rect
        x={hourEdge(peakStartHour)}
        y={m.t}
        width={(iw * (peakEndHour - peakStartHour)) / 24}
        height={batteryBottom - m.t}
        fill="var(--tint)"
      />
      <text x={hourEdge(peakStartHour + 2)} y={m.t + 12} textAnchor="middle" className="em pri">
        Peak
      </text>
      {[0, 3, 6].map((v) => (
        <g key={`kw-${v}`}>
          <line className="gridline" x1={m.l} x2={w - m.r} y1={ySolar(v)} y2={ySolar(v)} />
          <text x={m.l - 8} y={ySolar(v) + 4} textAnchor="end">
            {`${v}${v === 6 ? ' kW' : ''}`}
          </text>
        </g>
      ))}
      {[0, 50, 100].map((v) => (
        <g key={`pct-${v}`}>
          <line className="gridline" x1={m.l} x2={w - m.r} y1={yBattery(v)} y2={yBattery(v)} />
          <text x={m.l - 8} y={yBattery(v) + 4} textAnchor="end">
            {`${v}%`}
          </text>
        </g>
      ))}
      <text x={m.l} y={batteryTop - 8} className="lbl">
        Battery
      </text>
      {ticks.map((hour) => (
        <text key={hour} x={x(hour)} y={h - 5} textAnchor="middle">
          {`${pad(hour)}:00`}
        </text>
      ))}
      <path d={smoothArea(solarPoints, ySolar(0))} className="fade" fill={`url(#${id}-gs)`} />
      <path
        className="draw"
        pathLength={1}
        d={smooth(solarPoints)}
        fill="none"
        stroke="var(--c-solar)"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        className="fade"
        d={smoothArea(solarPoints, ySolar(0))}
        fill="var(--c-solar)"
        opacity=".26"
        clipPath={`url(#${id}-cu)`}
      />
      <circle
        cx={x(peakIndex)}
        cy={ySolar(peakKw)}
        r="3.5"
        fill="#fff"
        stroke="var(--c-solar)"
        strokeWidth="2"
      />
      {showPeakLabel && (
        <text x={x(peakIndex)} y={ySolar(peakKw) - 10} textAnchor="middle" className="em">
          {`${peakKw.toFixed(1)} kW`}
        </text>
      )}
      <path
        d={smooth(loadPoints)}
        className="halo"
        fill="none"
        strokeWidth="5"
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity=".85"
      />
      <path
        className="draw"
        pathLength={1}
        d={smooth(loadPoints)}
        fill="none"
        stroke="var(--text)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <path d={smoothArea(batteryPoints, yBattery(0))} className="fade" fill={`url(#${id}-gb)`} />
      <path
        className="draw"
        pathLength={1}
        d={smooth(batteryPoints)}
        fill="none"
        stroke="var(--primary)"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </>
  );
});
