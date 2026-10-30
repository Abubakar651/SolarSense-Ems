'use client';

import { useState, type PointerEvent } from 'react';
import { useChartFrame } from '@/hooks/use-chart-frame';
import { smooth, type Point } from '@/lib/charts/smooth';
import { cn } from '@/lib/cn';
import { ChartTooltip, type TooltipState } from './chart-tooltip';
import { FadeGradient } from './gradient';

export interface LineSeries {
  /** `null` leaves a gap at that point. */
  values: (number | null)[];
  color: string;
  dashed?: boolean;
  name?: string;
}

interface LineChartProps {
  id: string;
  xs: (string | number)[];
  series: LineSeries[];
  height?: number;
  yMin: number;
  yMax: number;
  yFormat: (value: number) => string;
  xEvery?: number;
  /** Index of a vertical "Today" marker. */
  marker?: number;
  tipHead?: (x: string | number) => string;
  ariaLabel: string;
}

const MARGIN = { l: 44, r: 12, t: 14, b: 26 } as const;
const IDLE_TIP: TooltipState = { visible: false, x: 0, y: 0, head: '', rows: [] };

/** Line chart with a soft area under the first series, a hover crosshair and a tooltip. */
export function LineChart({
  id,
  xs,
  series,
  height = 220,
  yMin,
  yMax,
  yFormat,
  xEvery = 2,
  marker,
  tipHead,
  ariaLabel,
}: LineChartProps) {
  const { ref, width, first } = useChartFrame<HTMLDivElement>();
  const [crosshair, setCrosshair] = useState<number | null>(null);
  const [tip, setTip] = useState<TooltipState>(IDLE_TIP);

  const n = xs.length;
  const iw = width - MARGIN.l - MARGIN.r;
  const ih = height - MARGIN.t - MARGIN.b;
  const X = (i: number) => MARGIN.l + (iw * i) / (n - 1);
  const Y = (v: number) => MARGIN.t + ih * (1 - (v - yMin) / (yMax - yMin));
  const pointsOf = (s: LineSeries): Point[] =>
    s.values.flatMap((v, i): Point[] => (v === null ? [] : [[X(i), Y(v)]]));
  const lead = pointsOf(series[0] as LineSeries);
  const lastPoint = lead[lead.length - 1] as Point;
  const firstPoint = lead[0] as Point;
  const gradientId = `${id}-lg`;

  const move = (event: PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const i = Math.max(
      0,
      Math.min(n - 1, Math.round(((event.clientX - rect.left) / rect.width) * (n - 1))),
    );
    const present = series.filter((s) => s.values[i] != null);
    setCrosshair(i);
    if (!present.length) return;
    setTip({
      visible: true,
      x: X(i),
      y: Y(Math.max(...present.map((s) => s.values[i] as number))),
      head: tipHead ? tipHead(xs[i] as string | number) : String(xs[i]),
      rows: present.map((s) => ({
        color: s.color,
        name: s.name ?? 'Value',
        value: yFormat(s.values[i] as number),
      })),
    });
  };
  const leave = () => {
    setCrosshair(null);
    setTip((current) => ({ ...current, visible: false }));
  };

  return (
    <div className={cn('chart', first && 'first')} id={id} ref={ref}>
      {width > 0 && (
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
          <defs>
            <FadeGradient id={gradientId} />
          </defs>
          {[0, 1, 2, 3, 4].map((k) => {
            const v = yMin + ((yMax - yMin) * k) / 4;
            return (
              <g key={k}>
                <line
                  className="gridline"
                  x1={MARGIN.l}
                  x2={width - MARGIN.r}
                  y1={Y(v)}
                  y2={Y(v)}
                />
                <text x={MARGIN.l - 8} y={Y(v) + 4} textAnchor="end">
                  {yFormat(v)}
                </text>
              </g>
            );
          })}
          {xs.map(
            (label, i) =>
              i % xEvery === 0 && (
                <text key={i} x={X(i)} y={height - 6} textAnchor="middle">
                  {label}
                </text>
              ),
          )}
          <path
            d={`${smooth(lead)} L${lastPoint[0]},${Y(yMin)} L${firstPoint[0]},${Y(yMin)}Z`}
            className="fade"
            fill={`url(#${gradientId})`}
          />
          {series.map((s, index) => (
            <path
              key={index}
              className={s.dashed ? undefined : 'draw'}
              pathLength={s.dashed ? undefined : 1}
              fill="none"
              stroke={s.color}
              strokeWidth="2.25"
              strokeDasharray={s.dashed ? '5 5' : undefined}
              strokeLinejoin="round"
              strokeLinecap="round"
              d={smooth(pointsOf(s))}
            />
          ))}
          <circle cx={lastPoint[0]} cy={lastPoint[1]} r="9" fill="var(--primary)" opacity=".16" />
          <circle
            cx={lastPoint[0]}
            cy={lastPoint[1]}
            r="4.5"
            fill="#fff"
            stroke="var(--primary)"
            strokeWidth="2.25"
          />
          {marker !== undefined && (
            <>
              <line
                x1={X(marker)}
                x2={X(marker)}
                y1={MARGIN.t}
                y2={MARGIN.t + ih}
                stroke="var(--text)"
                strokeDasharray="3 4"
              />
              <text x={X(marker)} y={MARGIN.t + 10} dx={-5} textAnchor="end" className="em">
                Today
              </text>
            </>
          )}
          <line
            x1={crosshair === null ? undefined : X(crosshair)}
            x2={crosshair === null ? undefined : X(crosshair)}
            y1={MARGIN.t}
            y2={MARGIN.t + ih}
            stroke="var(--primary)"
            strokeWidth="1.5"
            opacity={crosshair === null ? 0 : 1}
          />
          <rect
            x={MARGIN.l}
            y={MARGIN.t}
            width={iw}
            height={ih}
            fill="transparent"
            onPointerMove={move}
            onPointerLeave={leave}
          />
        </svg>
      )}
      <ChartTooltip tip={tip} containerWidth={width} />
    </div>
  );
}
