import type { Metadata } from 'next';
import { PageHeader } from '@/components/ui/page-header';
import { ClockBadge } from '@/features/dashboard/components/clock-badge';
import { attentionItems } from '@/features/dashboard/attention';
import { DashboardLive } from '@/features/dashboard/components/dashboard-live';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Dashboard' };

export default async function DashboardPage() {
  const { energy, panels, outage } = getServices();
  const [plan, soiling, outageData] = await Promise.all([
    energy.getDayPlan(),
    panels.getSoiling(),
    outage.getOutage(),
  ]);

  return (
    <section data-route="dashboard">
      <PageHeader title="Good afternoon, Zaeem">
        Here is how your system is doing right now. <ClockBadge />
      </PageHeader>
      <DashboardLive plan={plan} attention={attentionItems(plan, soiling, outageData)} />
    </section>
  );
}
