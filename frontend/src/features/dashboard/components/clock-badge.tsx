'use client';

import { pad } from '@/lib/format';
import { useSampleClock } from '@/providers/sample-clock-provider';

/** "Sample data · 15:42" tag that follows the sample clock. */
export function ClockBadge() {
  const { hour, minute } = useSampleClock();

  return (
    <span className="badge b-warn" style={{ marginLeft: 6 }}>
      <span>{`Sample data · ${pad(hour)}:${pad(minute)}`}</span>
    </span>
  );
}
