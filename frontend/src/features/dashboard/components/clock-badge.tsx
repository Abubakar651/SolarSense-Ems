'use client';

import { pad } from '@/lib/format';
import { useSampleClock } from '@/providers/sample-clock-provider';

/** "Sample data · 15:42" for a replayed day, "Live · 15:42" for today's live plan; follows the clock. */
export function ClockBadge({ sample }: { sample: boolean }) {
  const { hour, minute } = useSampleClock();

  return (
    <span className={`badge ${sample ? 'b-warn' : 'b-ok'}`} style={{ marginLeft: 6 }}>
      <span>{`${sample ? 'Sample data' : 'Live'} · ${pad(hour)}:${pad(minute)}`}</span>
    </span>
  );
}
