'use client';

import { useEffect, useState } from 'react';
import type { InverterReading } from '@/types/domain/inverter';

const POLL_MS = 30_000;
const UNREADABLE: InverterReading = { status: 'offline', message: 'The inverter reading failed.' };

/**
 * The latest inverter reading, refreshed every 30 s while the tab is visible. A failed poll counts
 * as offline. Null (sample data) never polls.
 */
export function useInverterReading(
  initial: InverterReading | null,
  read: () => Promise<InverterReading>,
): InverterReading | null {
  const [reading, setReading] = useState(initial);
  useEffect(() => {
    if (initial === null) return;
    let active = true;
    const timer = window.setInterval(() => {
      if (document.hidden) return;
      read().then(
        (next) => active && setReading(next),
        () => active && setReading(UNREADABLE),
      );
    }, POLL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [initial, read]);
  return reading;
}
