'use client';

import { useMemo, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { useChartFrame } from '@/hooks/use-chart-frame';
import { planLayout } from '@/lib/charts/plan-layout';
import { cn } from '@/lib/cn';
import { pad } from '@/lib/format';
import { ChartTooltip, type TooltipState } from './chart-tooltip';
import { PlanChartStatic, type PlanSeries } from './plan-chart-svg';

const ARIA_LABEL =
  'Chart of one day. Solar output as an area, home usage as a line, and battery level in a strip below. The battery is nearly full before the evening peak and drains during it.';
const HOURS = 24;

interface PlanChartProps {
  /** Unique per chart on the page: prefixes SVG ids. */
  id: string;
  /** Matches the id of the readout paragraph rendered below the chart. */
  readoutId: string;
  series: PlanSeries & { grid: number[] };
  /** Sample clock; the "Now" marker follows it. */
  now: { hour: number; minute: number };
  /** Chart height in px for narrow (<480) and wide containers. */
  height: { narrow: number; wide: number };
}

const IDLE_TIP: TooltipState = { visible: false, x: 0, y: 0, head: '', rows: [] };

/** 24-hour solar / usage / battery chart with a keyboard- and pointer-driven hour scrubber. */
export function PlanChart({ id, readoutId, series, now, height }: PlanChartProps) {
  const { ref, width, first } = useChartFrame<HTMLDivElement>();
  const [hovered, setHovered] = useState<number | null>(null);
  const [tip, setTip] = useState<TooltipState>(IDLE_TIP);

  const h = width < 480 ? height.narrow : height.wide;
  const layout = useMemo(() => planLayout(width, h), [width, h]);
  const hour = hovered ?? now.hour;
  const { solar, load, soc, grid } = series;
  const nowX = layout.nowX(now.hour, now.minute);
  const peakX = layout.x(solar.indexOf(Math.max(...solar)));
  const showPeakLabel = Math.abs(peakX - nowX) > 56;
  const nowLabelOnLeft = nowX > width - 60 || width < 480;

  const show = (index: number) => {
    const i = Math.max(0, Math.min(HOURS - 1, index));
    setHovered(i);
    setTip({
      visible: true,
      x: layout.x(i),
      y: layout.m.t + 90,
      head: `${pad(i)}:00`,
      rows: [
        { color: 'var(--c-solar)', name: 'Solar', value: `${(solar[i] as number).toFixed(1)} kW` },
        { color: '#fff', name: 'Usage', value: `${(load[i] as number).toFixed(1)} kW` },
        { color: 'var(--tint-3)', name: 'Battery', value: `${soc[i]}%` },
        { color: '#94A3B8', name: 'Grid import', value: `${(grid[i] as number).toFixed(1)} kW` },
      ],
    });
  };
  const hide = () => {
    setHovered(null);
    setTip((current) => ({ ...current, visible: false }));
  };
  const indexAt = (event: PointerEvent<SVGRectElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    return Math.floor(((event.clientX - rect.left) / rect.width) * HOURS);
  };
  const onKeyDown = (event: KeyboardEvent<SVGRectElement>) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (step !== undefined) show(hour + step);
    else if (event.key === 'Home') show(0);
    else if (event.key === 'End') show(HOURS - 1);
    else return;
    event.preventDefault();
  };

  const text = (n: number) => n.toFixed(1);
  const readout = [
    `${pad(hour)}:00`,
    ` · Solar `,
    `${text(solar[hour] as number)} kW`,
    ` · Usage `,
    `${text(load[hour] as number)} kW`,
    ` · Battery `,
    `${soc[hour]}%`,
    ` · Grid import `,
    `${text(grid[hour] as number)} kW`,
  ];

  return (
    <>
      <div className={cn('chart', first && 'first')} id={id} ref={ref}>
        {width > 0 && (
          <svg viewBox={`0 0 ${width} ${h}`}>
            <g role="img" aria-label={ARIA_LABEL}>
              <PlanChartStatic
                id={id}
                w={width}
                h={h}
                layout={layout}
                series={series}
                showPeakLabel={showPeakLabel}
              />
              <line
                x1={nowX}
                x2={nowX}
                y1={layout.m.t}
                y2={layout.batteryBottom}
                stroke="var(--text)"
                strokeDasharray="3 4"
              />
              <text
                x={nowX}
                y={layout.m.t + 12}
                dx={nowLabelOnLeft ? -5 : 5}
                textAnchor={nowLabelOnLeft ? 'end' : 'start'}
                className="em"
              >
                Now
              </text>
              <circle className="nowring" cx={nowX} cy={layout.m.t} r="3.5" />
              <circle cx={nowX} cy={layout.m.t} r="3.5" style={{ fill: 'var(--text)' }} />
            </g>
            <PlanCursor layout={layout} hour={hour} visible={hovered !== null} series={series} />
            <rect
              x={layout.m.l}
              y={layout.m.t}
              width={layout.iw}
              height={layout.batteryBottom - layout.m.t}
              fill="transparent"
              tabIndex={0}
              role="slider"
              aria-label="Inspect hour of the day"
              aria-valuemin={0}
              aria-valuemax={23}
              aria-valuenow={hour}
              aria-valuetext={`${pad(hour)}:00, solar ${text(solar[hour] as number)} kilowatts, battery ${soc[hour]} percent`}
              onPointerMove={(event) => show(indexAt(event))}
              onPointerDown={(event) => show(indexAt(event))}
              onPointerLeave={hide}
              onBlur={hide}
              onKeyDown={onKeyDown}
            />
          </svg>
        )}
        <ChartTooltip tip={tip} containerWidth={width} />
      </div>
      <p className="readout" id={readoutId} aria-live="off">
        <b>{readout[0]}</b>
        {readout[1]}
        <b>{readout[2]}</b>
        {readout[3]}
        <b>{readout[4]}</b>
        {readout[5]}
        <b>{readout[6]}</b>
        {readout[7]}
        <b>{readout[8]}</b>
      </p>
    </>
  );
}

interface CursorProps {
  layout: ReturnType<typeof planLayout>;
  hour: number;
  visible: boolean;
  series: PlanSeries;
}

/** Vertical guide plus one dot per series at the inspected hour. */
function PlanCursor({ layout, hour, visible, series }: CursorProps) {
  const x = layout.x(hour);
  const opacity = visible ? 1 : 0;
  return (
    <>
      <line
        x1={x}
        x2={x}
        y1={layout.m.t}
        y2={layout.batteryBottom}
        stroke="var(--primary)"
        strokeWidth="1.5"
        opacity={opacity}
      />
      <circle
        cx={x}
        cy={layout.ySolar(series.solar[hour] as number)}
        r="4"
        fill="#fff"
        stroke="var(--c-solar)"
        strokeWidth="2"
        opacity={opacity}
      />
      <circle
        cx={x}
        cy={layout.ySolar(series.load[hour] as number)}
        r="4"
        fill="#fff"
        stroke="var(--text)"
        strokeWidth="2"
        opacity={opacity}
      />
      <circle
        cx={x}
        cy={layout.yBattery(series.soc[hour] as number)}
        r="4"
        fill="#fff"
        stroke="var(--primary)"
        strokeWidth="2"
        opacity={opacity}
      />
    </>
  );
}
