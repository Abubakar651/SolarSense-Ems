'use client';

import { BarChart } from '@/components/charts/bar-chart';
import { pad } from '@/lib/format';
import { riskLevel } from '../view-model';

const HOURS = Array.from({ length: 24 }, (_, hour) => pad(hour));

/** Hourly outage-risk bars; darker bars mean higher risk. */
export function RiskChart({ riskByHour }: { riskByHour: number[] }) {
  return (
    <BarChart
      id="chart-risk"
      values={riskByHour}
      labels={HOURS}
      height={240}
      level={riskByHour.map(riskLevel)}
      max={Math.max(5, Math.ceil(Math.max(...riskByHour) / 5) * 5)}
      showValues
      valueFormat={(v) => `${v}%`}
      axisFormat={(v) => `${v}%`}
      tipName="Days with an outage"
      tipFormat={(v) => `${v}%`}
      tipHead={(label) => `${label}:00`}
      labelEvery={(width) => (width < 560 ? 3 : 1)}
      ariaLabel="Bar chart of how often the grid has failed in each hour of the day."
    />
  );
}
