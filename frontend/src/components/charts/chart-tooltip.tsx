'use client';

import { useLayoutEffect, useRef } from 'react';

export interface TooltipRow {
  color: string;
  name: string;
  value: string;
}

export interface TooltipState {
  visible: boolean;
  /** Anchor point inside the chart container (px). */
  x: number;
  y: number;
  head: string;
  rows: TooltipRow[];
}

const GAP = 14;

/** Floating value card; flips to the left of the anchor near the right edge. */
export function ChartTooltip({
  tip,
  containerWidth,
}: {
  tip: TooltipState;
  containerWidth: number;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || !tip.visible) return;
    const width = el.offsetWidth;
    const left = tip.x + GAP + width > containerWidth ? tip.x - GAP - width : tip.x + GAP;
    el.style.left = `${Math.max(4, Math.min(containerWidth - width - 4, left))}px`;
    el.style.top = `${Math.max(0, tip.y - el.offsetHeight - 8)}px`;
  }, [tip, containerWidth]);

  return (
    <div className="tip" ref={ref} aria-hidden="true" style={{ opacity: tip.visible ? 1 : 0 }}>
      <div className="th">{tip.head}</div>
      {tip.rows.map((row) => (
        <div className="tr" key={row.name}>
          <span>
            <i style={{ background: row.color }} />
            {row.name}
          </span>
          <b>{row.value}</b>
        </div>
      ))}
    </div>
  );
}
