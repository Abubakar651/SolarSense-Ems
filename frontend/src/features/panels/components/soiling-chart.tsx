'use client';

import { LineChart } from '@/components/charts/line-chart';
import type { SoilingData } from '@/types/domain/panels';
import { forecastSeries } from '../view-model';

export function SoilingChart({ soiling }: { soiling: SoilingData }) {
  const history = soiling.history;
  const today = history.length - 1;
  const daysShown = history.length + soiling.forecast.length;
  const padded = [...history, ...Array<null>(soiling.forecast.length).fill(null)];
  const forecastEnd = soiling.forecast[soiling.forecast.length - 1] as number;

  return (
    <LineChart
      id="chart-soil"
      xs={Array.from({ length: daysShown }, (_, day) => day)}
      series={[
        { values: padded, color: 'var(--primary)', name: 'Output lost' },
        {
          values: forecastSeries(soiling),
          color: 'var(--primary)',
          dashed: true,
          name: 'Forecast',
        },
      ]}
      tipHead={(day) => `Day ${day}`}
      yMin={0}
      yMax={Math.ceil(forecastEnd / 5) * 5}
      yFormat={(v) => `${v}%`}
      xEvery={2}
      marker={today}
      height={230}
      ariaLabel={`Line chart of output lost to dust since the last wash: ${history[today]} percent on the latest day, forecast to reach ${forecastEnd} percent in ${soiling.forecast.length} more days.`}
    />
  );
}
