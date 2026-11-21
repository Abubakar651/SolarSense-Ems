'use client';

import { useRouter } from 'next/navigation';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { clockInKarachi } from '@/lib/dates';
import type { ClockTime } from '@/types/domain/energy';

const TICK_MS = 60_000;
const ClockContext = createContext<ClockTime | null>(null);

/** Next minute, stopping at 23:59 (the sample day does not roll over). */
export function advanceMinute({ hour, minute }: ClockTime): ClockTime {
  if (hour === 23 && minute === 59) return { hour, minute };
  return minute === 59 ? { hour: hour + 1, minute: 0 } : { hour, minute: minute + 1 };
}

/** True once the wall clock has passed midnight since `previous` (the hour wrapped round). */
export function crossedMidnight(previous: ClockTime, next: ClockTime): boolean {
  return next.hour * 60 + next.minute < previous.hour * 60 + previous.minute;
}

/**
 * The clock every live element follows ("Now" markers, countdowns, KPIs); consumers re-render, the rest
 * of the page does not. Live, it is the real time in Lahore and the page refetches today's plan once the
 * day changes. For sample data it starts at the sample day's time and advances once a minute.
 */
export function SampleClockProvider({
  start,
  live = false,
  children,
}: {
  start: ClockTime;
  live?: boolean;
  children: ReactNode;
}) {
  const [time, setTime] = useState(start);
  const router = useRouter();

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (!live) {
        setTime(advanceMinute);
        return;
      }
      const now = clockInKarachi(new Date());
      setTime((previous) => {
        // Refreshing re-renders the layout, which hands this provider the new day's plan.
        if (crossedMidnight(previous, now)) router.refresh();
        return now;
      });
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, [live, router]);

  return <ClockContext.Provider value={time}>{children}</ClockContext.Provider>;
}

export function useSampleClock(): ClockTime {
  const time = useContext(ClockContext);
  if (!time) throw new Error('useSampleClock must be used inside <SampleClockProvider>');
  return time;
}
