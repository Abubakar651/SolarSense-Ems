import type { Metadata } from 'next';
import { PageHeader } from '@/components/ui/page-header';
import { ClockBadge } from '@/features/dashboard/components/clock-badge';
import { attentionItems } from '@/features/dashboard/attention';
import { readInverterAction } from '@/features/dashboard/actions';
import { DashboardLive } from '@/features/dashboard/components/dashboard-live';
import { zeroDayPlan } from '@/features/dashboard/view-model';
import { CollectingBadge } from '@/features/history/components/collecting-badge';
import { firstName, greetingForHour, hourInKarachi } from '@/features/dashboard/greeting';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Dashboard' };

const PLAN_UNAVAILABLE_MESSAGE =
  "Today's plan isn't available right now: the weather forecast it is made from couldn't be fetched.";

export default async function DashboardPage() {
  const { account, energy, panels, outage, inverter } = getServices();
  const [user, planResult, soiling, outageData] = await Promise.all([
    account.getMe(),
    energy.getDayPlan(),
    panels.getSoiling(),
    outage.getOutage(),
  ]);
  const title = `${greetingForHour(hourInKarachi(new Date()))}, ${firstName(user.name)}`;
  const ready = planResult.status === 'ready';
  const plan = ready ? planResult.plan : zeroDayPlan();
  // A replayed sample day has no matching inverter; only a live, ready plan reads the inverter.
  const initialReading = ready && !plan.isSample ? await inverter.getLive() : null;

  return (
    <section data-route="dashboard">
      <PageHeader title={title}>
        <ClockBadge sample={plan.isSample} />
        {!ready && (
          <CollectingBadge
            result={{ status: planResult.status, loggedDays: 0 }}
            unavailableMessage={PLAN_UNAVAILABLE_MESSAGE}
          />
        )}
      </PageHeader>
      <DashboardLive
        plan={plan}
        attention={attentionItems(plan, soiling, outageData)}
        initialReading={initialReading}
        readInverter={readInverterAction}
      />
    </section>
  );
}
