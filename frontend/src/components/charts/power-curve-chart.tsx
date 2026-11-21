'use client';

import { useState, type PointerEvent } from 'react';
import { CURVE_COLORS, hoursOf, kwRange, linePath } from '@/features/energy/curve';
import { useChartFrame } from '@/hooks/use-chart-frame';
import type { CurvePoint } from '@/types/domain/energy';
import { ChartTooltip, type TooltipState } from './chart-tooltip';

interface PowerCurveChartProps {
  id: string;
  points: CurvePoint[];
  height?: number;
  ariaLabel: string;
}

const MARGIN = { l: 44, r: 12, t: 22, b: 26 } as const;
const SOC_HEIGHT = 64;
const SOC_GAP = 22;
const HOUR_LABELS = [0, 3, 6, 9, 12, 15, 18, 21] as const;
const IDLE_TIP: TooltipState = { visible: false, x: 0, y: 0, head: '', rows: [] };

const kw = (value: number) => `${value.toFixed(2)} kW`;
const signed = (value: number) => `${value > 0 ? '+' : ''}${value.toFixed(2)} kW`;

/**
 * One day of power: solar as an area, home usage, battery (+ charging) and grid (+ exporting) as lines on a
 * kW axis, with the battery level in a strip underneath. Points sit at their time of day, so a partial day
 * or a gap in the log draws as it happened.
 */
export function PowerCurveChart({ id, points, height = 300, ariaLabel }: PowerCurveChartProps) {
  const { ref, width } = useChartFrame<HTMLDivElement>();
  const [crosshair, setCrosshair] = useState<number | null>(null);
  const [tip, setTip] = useState<TooltipState>(IDLE_TIP);

  const hasSoc = points.some((p) => p.socPct !== null);
  const hasBattery = points.some((p) => p.batteryKw !== null);
  const hasGrid = points.some((p) => p.gridKw !== null);
  const total = height + (hasSoc ? SOC_GAP + SOC_HEIGHT : 0);
  const { min, max } = kwRange(points);
  const iw = width - MARGIN.l - MARGIN.r;
  const ih = height - MARGIN.t - MARGIN.b;
  const X = (p: CurvePoint) => MARGIN.l + (hoursOf(p.time) / 24) * iw;
  const Y = (v: number) => MARGIN.t + ih * (1 - (v - min) / (max - min));
  const socTop = height + SOC_GAP - 6;
  const SY = (v: number) => socTop + SOC_HEIGHT * (1 - v / 100);
  const labelEvery = width < 520 ? 6 : 3;

  const move = (event: PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const hour = ((event.clientX - rect.left) / rect.width) * 24;
    let nearest = 0;
    points.forEach((p, i) => {
      if (Math.abs(hoursOf(p.time) - hour) < Math.abs(hoursOf(points[nearest]!.time) - hour)) {
        nearest = i;
      }
    });
    const p = points[nearest] as CurvePoint;
    const top = Math.max(p.pvKw, p.loadKw, p.batteryKw ?? 0, p.gridKw ?? 0);
    setCrosshair(nearest);
    setTip({
      visible: true,
      x: X(p),
      y: Y(top),
      head: p.time,
      rows: [
        { color: CURVE_COLORS.pv, name: 'Solar', value: kw(p.pvKw) },
        { color: CURVE_COLORS.load, name: 'Home', value: kw(p.loadKw) },
        ...(p.batteryKw === null
          ? []
          : [{ color: CURVE_COLORS.battery, name: 'Battery', value: signed(p.batteryKw) }]),
        ...(p.gridKw === null
          ? []
          : [{ color: CURVE_COLORS.grid, name: 'Grid', value: signed(p.gridKw) }]),
        ...(p.socPct === null
          ? []
          : [{ color: 'var(--tint-3)', name: 'Battery level', value: `${p.socPct}%` }]),
      ],
    });
  };
  const leave = () => {
    setCrosshair(null);
    setTip((current) => ({ ...current, visible: false }));
  };

  const first = points[0];
  const last = points[points.length - 1];
  const ticks = [0, 1, 2, 3, 4].map((k) => min + ((max - min) * k) / 4);
  const at = crosshair === null ? null : (points[crosshair] as CurvePoint);

  return (
    <div className="chart" id={id} ref={ref}>
      {width > 0 && first && last && (
        <svg viewBox={`0 0 ${width} ${total}`} role="img" aria-label={ariaLabel}>
          {ticks.map((v) => (
            <g key={v}>
              <line className="gridline" x1={MARGIN.l} x2={width - MARGIN.r} y1={Y(v)} y2={Y(v)} />
              <text x={MARGIN.l - 8} y={Y(v) + 4} textAnchor="end">
                {Number.isInteger(v) ? v : v.toFixed(1)}
              </text>
            </g>
          ))}
          <text x={MARGIN.l - 8} y={10} textAnchor="end">
            kW
          </text>
          {min < 0 && (
            <line
              x1={MARGIN.l}
              x2={width - MARGIN.r}
              y1={Y(0)}
              y2={Y(0)}
              stroke="var(--line-strong)"
            />
          )}
          {HOUR_LABELS.map(
            (h) =>
              h % labelEvery === 0 && (
                <text key={h} x={MARGIN.l + (h / 24) * iw} y={height - 6} textAnchor="middle">
                  {`${String(h).padStart(2, '0')}:00`}
                </text>
              ),
          )}
          <path
            d={`M${X(first).toFixed(1)},${Y(0)} ${points.map((p) => `L${X(p).toFixed(1)},${Y(p.pvKw).toFixed(1)}`).join(' ')} L${X(last).toFixed(1)},${Y(0)}Z`}
            fill="var(--accent)"
            opacity=".22"
          />
          <path
            d={linePath(points, (p) => p.pvKw, X, Y)}
            fill="none"
            stroke={CURVE_COLORS.pv}
            strokeWidth="2"
            strokeLinejoin="round"
          />
          {hasGrid && (
            <path
              d={linePath(points, (p) => p.gridKw, X, Y)}
              fill="none"
              stroke={CURVE_COLORS.grid}
              strokeWidth="1.5"
              strokeDasharray="4 3"
              strokeLinejoin="round"
            />
          )}
          {hasBattery && (
            <path
              d={linePath(points, (p) => p.batteryKw, X, Y)}
              fill="none"
              stroke={CURVE_COLORS.battery}
              strokeWidth="1.75"
              strokeLinejoin="round"
            />
          )}
          <path
            d={linePath(points, (p) => p.loadKw, X, Y)}
            fill="none"
            stroke={CURVE_COLORS.load}
            strokeWidth="2"
            strokeLinejoin="round"
          />
          {hasSoc && (
            <>
              {[0, 50, 100].map((v) => (
                <g key={v}>
                  <line
                    className="gridline"
                    x1={MARGIN.l}
                    x2={width - MARGIN.r}
                    y1={SY(v)}
                    y2={SY(v)}
                  />
                  <text x={MARGIN.l - 8} y={SY(v) + 4} textAnchor="end">
                    {`${v}%`}
                  </text>
                </g>
              ))}
              <path
                d={linePath(points, (p) => p.socPct, X, SY)}
                fill="none"
                stroke="var(--primary)"
                strokeWidth="1.75"
                strokeLinejoin="round"
              />
            </>
          )}
          {at && (
            <line
              x1={X(at)}
              x2={X(at)}
              y1={MARGIN.t}
              y2={hasSoc ? socTop + SOC_HEIGHT : height - MARGIN.b}
              stroke="var(--primary)"
              strokeWidth="1.5"
            />
          )}
          <rect
            x={MARGIN.l}
            y={MARGIN.t}
            width={iw}
            height={hasSoc ? socTop + SOC_HEIGHT - MARGIN.t : ih}
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
