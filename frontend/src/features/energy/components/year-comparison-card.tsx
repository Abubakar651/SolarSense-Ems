'use client';

import { GroupedBarChart } from '@/components/charts/grouped-bar-chart';
import { CardHeader } from '@/components/ui/card-header';
import type { MonthEnergy } from '@/types/domain/energy';
import { yearComparison } from '../comparison';

const PREVIOUS_COLOR = 'var(--tint-3)';
const CURRENT_COLOR = 'var(--accent)';

/** Solar generated each month, this year beside last year. Nothing until a month exists in both. */
export function YearComparisonCard({ months }: { months: readonly MonthEnergy[] }) {
  const comparison = yearComparison(months);
  if (comparison === null) return null;
  const { previousYear, currentYear } = comparison;

  return (
    <div className="card">
      <CardHeader title="Generation by year" subtitle="kWh per month" />
      <div className="legend" aria-hidden="true">
        <span>
          <i className="sw" style={{ background: PREVIOUS_COLOR }} />
          {previousYear}
        </span>
        <span>
          <i className="sw" style={{ background: CURRENT_COLOR }} />
          {currentYear}
        </span>
      </div>
      <GroupedBarChart
        id="chart-yoy"
        labels={comparison.labels}
        yFormat={String}
        labelEvery={(width) => (width < 500 ? 2 : 1)}
        ariaLabel={`Bar chart of solar generated each month in ${previousYear} and ${currentYear}, in kWh.`}
        series={[
          { name: previousYear, color: PREVIOUS_COLOR, values: comparison.previous },
          { name: currentYear, color: CURRENT_COLOR, values: comparison.current },
        ]}
      />
    </div>
  );
}
