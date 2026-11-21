import { redirect } from 'next/navigation';
import type { ReactNode } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { markAlertReadAction, markAllAlertsReadAction } from '@/features/alerts/actions';
import { logoutAction } from '@/features/auth/actions';
import { AlertsProvider } from '@/providers/alerts-provider';
import { clockInKarachi } from '@/lib/dates';
import { SampleClockProvider } from '@/providers/sample-clock-provider';
import { getServices } from '@/services';

export default async function AppGroupLayout({ children }: { children: ReactNode }) {
  const { account, alerts, energy } = getServices();
  const user = await account.getMe();
  if (!user.onboarded) redirect('/onboarding');
  const [alertList, planResult] = await Promise.all([alerts.listAlerts(), energy.getDayPlan()]);
  // Without a plan yet the clock is still the real time; the pages say why there is no plan.
  const plan = planResult.status === 'ready' ? planResult.plan : null;

  return (
    <AlertsProvider
      initial={alertList}
      persistReadAll={markAllAlertsReadAction}
      persistReadOne={markAlertReadAction}
    >
      <SampleClockProvider
        start={plan?.clockStart ?? clockInKarachi(new Date())}
        live={!(plan?.isSample ?? false)}
      >
        <AppShell user={user} logout={logoutAction} sample={plan?.isSample ?? false}>
          {children}
        </AppShell>
      </SampleClockProvider>
    </AlertsProvider>
  );
}
