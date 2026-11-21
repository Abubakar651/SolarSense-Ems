import type { Metadata } from 'next';
import { PageHeader } from '@/components/ui/page-header';
import { EnergyMonitoringCard } from '@/features/energy/components/energy-monitoring-card';
import { PowerCurveCard } from '@/features/energy/components/power-curve-card';
import { SolarCalendar } from '@/features/energy/components/solar-calendar';
import { YearComparisonCard } from '@/features/energy/components/year-comparison-card';
import { zeroEnergyHistory } from '@/features/energy/monitoring';
import { CollectingBadge } from '@/features/history/components/collecting-badge';
import { FreshnessBadge } from '@/features/history/components/freshness-badge';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Energy' };

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

export default async function EnergyPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string | string[] }>;
}) {
  const { date } = await searchParams;
  const day = typeof date === 'string' && ISO_DATE.test(date) ? date : undefined;
  const { energy } = getServices();
  const [history, curve] = await Promise.all([energy.getEnergyHistory(), energy.getDayCurve(day)]);
  const data = history.status === 'ready' ? history.data : zeroEnergyHistory();

  return (
    <section data-route="energy">
      <PageHeader title="Energy">
        {history.status === 'ready' ? (
          <FreshnessBadge freshness={history.freshness} />
        ) : (
          <CollectingBadge result={history} />
        )}
      </PageHeader>
      <div className="grid">
        {curve && <PowerCurveCard curve={curve} />}
        <EnergyMonitoringCard history={data} />
        <YearComparisonCard months={data.months} />
        <SolarCalendar days={data.days} />
      </div>
    </section>
  );
}
