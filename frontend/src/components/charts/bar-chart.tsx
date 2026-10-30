'use client';

import { useState, type CSSProperties, type PointerEvent } from 'react';
import { useChartFrame } from '@/hooks/use-chart-frame';
import { niceMax } from '@/lib/charts/nice-max';
import { cn } from '@/lib/cn';
import { fmt } from '@/lib/format';
import { ChartTooltip, type TooltipState } from './chart-tooltip';

interface BarChartProps {
  id: string;
  values: number[];
  labels: string[];
  height?: number;
  /** Formats axis ticks, value labels and tooltips unless overridden. */
  format?: (value: number) => string;
  axisFormat?: (value: number) => string;
  valueFormat?: (value: number) => string;
  /** Formats the tooltip value and the "Avg" label. */
  tipFormat?: (value: number) => string;
  tipName?: string;
  tipHead?: (label: string) => string;
  /** 0/1/2 per bar: only changes opacity (low / medium / high). */
  level?: number[];
  showValues?: boolean;
  /** Fixed axis maximum; otherwise it is derived from the data. */
  max?: number;
  /** Show every n-th x label; may depend on the container width. */
  labelEvery?: number | ((width: number) => number);
  ariaLabel: string;
}

const MARGIN = { l: 44, r: 6, b: 24 } as const;
const LEVEL_OPACITY = [0.3, 0.62, 1] as const;
const IDLE_TIP: TooltipState = { visible: false, x: 0, y: 0, head: '', rows: [] };

/** Rounded gradient bars with an average line and a hover/touch tooltip. */
export function BarChart({
  id,
  values,
  labels,
  height = 220,
  format = fmt,
  axisFormat,
  valueFormat,
  tipFormat,
  tipName = 'Value',
  tipHead,
  level,
  showValues,
  max: fixedMax,
  labelEvery: labelEveryProp = 1,
  ariaLabel,
}: BarChartProps) {
  const { ref, width, first } = useChartFrame<HTMLDivElement>();
  const [active, setActive] = useState(-1);
  const [tip, setTip] = useState<TooltipState>(IDLE_TIP);

  const labelEvery = typeof labelEveryProp === 'function' ? labelEveryProp(width) : labelEveryProp;
  const n = values.length;
  const top = showValues ? 22 : 10;
  const iw = width - MARGIN.l - MARGIN.r;
  const ih = height - top - MARGIN.b;
  const bw = iw / n;
  const { step, max } = fixedMax
    ? { step: fixedMax / 4, max: fixedMax }
    : niceMax(Math.max(...values) * 1.05);
  const y = (v: number) => top + ih * (1 - v / max);
  const average = values.reduce((a, b) => a + b, 0) / n;
  const gradientId = `${id}-bg`;
  const ticks: number[] = [];
  for (let v = 0; v <= max + 1e-9; v += step) ticks.push(v);

  const indexAt = (event: PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return Math.max(0, Math.min(n - 1, Math.floor(((event.clientX - rect.left) / rect.width) * n)));
  };
  const show = (event: PointerEvent<SVGRectElement>) => {
    const i = indexAt(event);
    setActive(i);
    setTip({
      visible: true,
      x: MARGIN.l + (i + 0.5) * bw,
      y: y(values[i] as number),
      head: tipHead ? tipHead(labels[i] as string) : (labels[i] as string),
      rows: [
        {
          color: 'var(--primary)',
          name: tipName,
          value: (tipFormat ?? format)(values[i] as number),
        },
      ],
    });
  };
  const hide = () => {
    setActive(-1);
    setTip((current) => ({ ...current, visible: false }));
  };

  const averageLabel = `Avg ${(tipFormat ?? format)(average)}`;
  const labelWidth = averageLabel.length * 6.6 + 12;

  return (
    <div className={cn('chart', first && 'first')} id={id} ref={ref}>
      {width > 0 && (
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={ariaLabel}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" style={{ stopColor: 'var(--primary)' }} />
              <stop offset="1" style={{ stopColor: 'var(--primary)', stopOpacity: 0.55 }} />
            </linearGradient>
          </defs>
          {ticks.map((v) => (
            <g key={v}>
              <line className="gridline" x1={MARGIN.l} x2={width - MARGIN.r} y1={y(v)} y2={y(v)} />
              <text x={MARGIN.l - 8} y={y(v) + 4} textAnchor="end">
                {(axisFormat ?? format)(v)}
              </text>
            </g>
          ))}
          {values.map((v, i) => {
            const barX = MARGIN.l + i * bw + bw * 0.18;
            const barW = Math.max(2, bw * 0.64);
            return (
              <g key={i}>
                <rect
                  className={cn('bar-r', active === i && 'on')}
                  style={{ '--i': i } as CSSProperties}
                  x={barX}
                  y={y(v)}
                  width={barW}
                  height={Math.max(0, y(0) - y(v))}
                  rx={Math.min(4, barW / 2)}
                  fill={`url(#${gradientId})`}
                  opacity={level ? LEVEL_OPACITY[level[i] as number] : 1}
                />
                {showValues && bw >= 24 && (
                  <text className="val" x={barX + barW / 2} y={y(v) - 6} textAnchor="middle">
                    {(valueFormat ?? format)(v)}
                  </text>
                )}
                {i % labelEvery === 0 && (
                  <text x={barX + barW / 2} y={height - 6} textAnchor="middle">
                    {labels[i]}
                  </text>
                )}
              </g>
            );
          })}
          {!level && n > 1 && (
            <>
              <line
                x1={MARGIN.l}
                x2={width - MARGIN.r}
                y1={y(average)}
                y2={y(average)}
                stroke="var(--text)"
                strokeWidth="1.25"
                strokeDasharray="5 4"
              />
              <rect
                x={width - MARGIN.r - labelWidth}
                y={y(average) - 22}
                width={labelWidth}
                height="20"
                rx="6"
                fill="#fff"
                stroke="var(--line-strong)"
              />
              <text
                className="em"
                x={width - MARGIN.r - labelWidth / 2}
                y={y(average) - 8}
                textAnchor="middle"
              >
                {averageLabel}
              </text>
            </>
          )}
          <rect
            x={MARGIN.l}
            y={top}
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
