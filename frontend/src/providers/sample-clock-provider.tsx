'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { ClockTime } from '@/types/domain/energy';

const TICK_MS = 60_000;
const ClockContext = createContext<ClockTime | null>(null);

/** Next minute, stopping at 23:59 (the sample day does not roll over). */
export function advanceMinute({ hour, minute }: ClockTime): ClockTime {
  if (hour === 23 && minute === 59) return { hour, minute };
  return minute === 59 ? { hour: hour + 1, minute: 0 } : { hour, minute: minute + 1 };
}

/**
 * The sample clock every live element follows ("Now" markers, countdowns, KPIs). It starts at the
 * mock site's time and advances once a minute; consumers re-render, the rest of the page does not.
 */
export function SampleClockProvider({
  start,
  children,
}: {
  start: ClockTime;
  children: ReactNode;
}) {
  const [time, setTime] = useState(start);

  useEffect(() => {
    const timer = window.setInterval(() => setTime(advanceMinute), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  return <ClockContext.Provider value={time}>{children}</ClockContext.Provider>;
}

export function useSampleClock(): ClockTime {
  const time = useContext(ClockContext);
  if (!time) throw new Error('useSampleClock must be used inside <SampleClockProvider>');
  return time;
}
