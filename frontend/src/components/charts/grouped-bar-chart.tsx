'use client';

import { useState, type PointerEvent } from 'react';
import { useChartFrame } from '@/hooks/use-chart-frame';
import { niceMax } from '@/lib/charts/nice-max';
import { cn } from '@/lib/cn';
import { ChartTooltip, type TooltipState } from './chart-tooltip';

export interface BarSeries {
  name: string;
  /** Any CSS colour, usually a token such as var(--accent). */
  color: string;
  /** `null` leaves that bar out. */
  values: (number | null)[];
}

interface GroupedBarChartProps {
  id: string;
  labels: string[];
  series: BarSeries[];
  height?: number;
  yFormat: (value: number) => string;
  /** Show every n-th x label; may depend on the container width. */
  labelEvery?: number | ((width: number) => number);
  tipHead?: (label: string) => string;
  ariaLabel: string;
}

const MARGIN = { l: 44, r: 6, t: 10, b: 24 } as const;
const GROUP_FILL = 0.76;
const IDLE_TIP: TooltipState = { visible: false, x: 0, y: 0, head: '', rows: [] };

/** One cluster of bars per label, one bar per series, with a hover/touch tooltip listing every series. */
export function GroupedBarChart({
  id,
  labels,
  series,
  height = 260,
  yFormat,
  labelEvery: labelEveryProp = 1,
  tipHead,
  ariaLabel,
}: GroupedBarChartProps) {
  const { ref, width, first } = useChartFrame<HTMLDivElement>();
  const [active, setActive] = useState(-1);
  const [tip, setTip] = useState<TooltipState>(IDLE_TIP);

  const labelEvery = typeof labelEveryProp === 'function' ? labelEveryProp(width) : labelEveryProp;
  const n = labels.length;
  const iw = width - MARGIN.l - MARGIN.r;
  const ih = height - MARGIN.t - MARGIN.b;
  const groupWidth = iw / n;
  const barWidth = Math.max(1.5, (groupWidth * GROUP_FILL) / series.length);
  const peak = Math.max(0, ...series.flatMap((s) => s.values.filter((v) => v !== null)));
  const { step, max } = niceMax(Math.max(peak, 1) * 1.05);
  const y = (v: number) => MARGIN.t + ih * (1 - v / max);
  const ticks: number[] = [];
  for (let v = 0; v <= max + 1e-9; v += step) ticks.push(v);

  const show = (event: PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const i = Math.max(
      0,
      Math.min(n - 1, Math.floor(((event.clientX - rect.left) / rect.width) * n)),
    );
    const rows = series.flatMap((s) =>
      s.values[i] == null ? [] : [{ color: s.color, name: s.name, value: yFormat(s.values[i]) }],
    );
    setActive(i);
    setTip({
      visible: rows.length > 0,
      x: MARGIN.l + (i + 0.5) * groupWidth,
      y: y(Math.max(0, ...series.map((s) => s.values[i] ?? 0))),
      head: tipHead ? tipHead(labels[i] as string) : (labels[i] as string),
      rows,
    });
  };
  const hide = () => {
    setActive(-1);
    setTip((current) => ({ ...current, visible: false }));
  };

  return (
    <div className={cn('chart', first && 'first')} id={id} ref={ref}>
      {width > 0 && (
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
          {ticks.map((v) => (
            <g key={v}>
              <line className="gridline" x1={MARGIN.l} x2={width - MARGIN.r} y1={y(v)} y2={y(v)} />
              <text x={MARGIN.l - 8} y={y(v) + 4} textAnchor="end">
                {yFormat(v)}
              </text>
            </g>
          ))}
          {labels.map((label, i) => {
            const clusterX =
              MARGIN.l + i * groupWidth + (groupWidth - barWidth * series.length) / 2;
            return (
              <g key={`${label}-${i}`} opacity={active === -1 || active === i ? 1 : 0.55}>
                {series.map((s, k) => {
                  const value = s.values[i];
                  if (value == null) return null;
                  return (
                    <rect
                      key={s.name}
                      className="gbar"
                      x={clusterX + k * barWidth}
                      y={y(value)}
                      width={Math.max(1, barWidth - 1)}
                      height={Math.max(0, y(0) - y(value))}
                      rx={Math.min(3, barWidth / 2)}
                      fill={s.color}
                    />
                  );
                })}
                {i % labelEvery === 0 && (
                  <text x={MARGIN.l + (i + 0.5) * groupWidth} y={height - 6} textAnchor="middle">
                    {label}
                  </text>
                )}
              </g>
            );
          })}
          <rect
            x={MARGIN.l}
            y={MARGIN.t}
            width={iw}
            height={ih}
            fill="transparent"
            onPointerMove={show}
            onPointerLeave={hide}
          />
        </svg>
      )}
      <ChartTooltip tip={tip} containerWidth={width} />
    </div>
  );
}
