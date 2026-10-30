'use client';

import { PlanChart } from '@/components/charts/plan-chart';
import { useSampleClock } from '@/providers/sample-clock-provider';
import type { DayPlan } from '@/types/domain/energy';

/** The 24-hour chart with its "Now" marker following the sample clock. */
export function PlanTimeline({ plan }: { plan: DayPlan }) {
  const now = useSampleClock();

  return (
    <PlanChart
      id="chart-plan"
      readoutId="plan-readout"
      series={plan}
      now={now}
      height={{ narrow: 250, wide: 300 }}
    />
  );
}
