'use client';

import { useEffect, useState } from 'react';
import { fmt } from '@/lib/format';
import { useReducedMotion } from './use-reduced-motion';

const DURATION_MS = 700;

/** Number of decimals in a displayed number ("3.1" -> 1, "486" -> 0). */
function decimalsOf(text: string): number {
  return (text.split('.')[1] ?? '').length;
}

/**
 * Counts from 0 up to `target` (a formatted string such as "3.1" or "1,250") once on mount.
 * Always renders the final text first (server render, reduced motion), so nothing depends on JS.
 */
export function useCountUp(target: string): string {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(target);

  useEffect(() => {
    const end = parseFloat(target.replace(/,/g, ''));
    if (reduced || !Number.isFinite(end)) return;
    const decimals = decimalsOf(target);
    let frame = 0;
    const start = performance.now();
    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / DURATION_MS);
      const value = end * (1 - (1 - progress) ** 3);
      setDisplay(progress < 1 ? (decimals ? value.toFixed(decimals) : fmt(value)) : target);
      if (progress < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, reduced]);

  return display;
}
