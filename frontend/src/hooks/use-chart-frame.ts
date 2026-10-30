'use client';

import { useEffect, useRef, useState } from 'react';

const DRAW_IN_MS = 1400;

/**
 * Measures a chart container's width (coalesced to one update per frame) and reports `first`
 * for the first draw-in only, so the entrance animation never replays on resize.
 */
export function useChartFrame<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  const [first, setFirst] = useState(false);
  const drawn = useRef(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    let frame = 0;
    let timer = 0;
    const measure = () => {
      if (element.clientWidth <= 0) return;
      setWidth(element.clientWidth);
      if (!drawn.current) {
        drawn.current = true;
        setFirst(true);
        timer = window.setTimeout(() => setFirst(false), DRAW_IN_MS);
      }
    };
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    });
    observer.observe(element);
    return () => {
      cancelAnimationFrame(frame);
      window.clearTimeout(timer);
      observer.disconnect();
    };
  }, []);

  return { ref, width, first };
}
