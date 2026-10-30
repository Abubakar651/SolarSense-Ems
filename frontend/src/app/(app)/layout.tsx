import type { ReactNode } from 'react';
import { AppShell } from '@/components/layout/app-shell';
import { AlertsProvider } from '@/providers/alerts-provider';
import { SampleClockProvider } from '@/providers/sample-clock-provider';
import { getServices } from '@/services';

export default async function AppGroupLayout({ children }: { children: ReactNode }) {
  const { alerts, energy } = getServices();
  const [alertList, plan] = await Promise.all([alerts.listAlerts(), energy.getDayPlan()]);

  return (
    <AlertsProvider initial={alertList}>
      <SampleClockProvider start={plan.clockStart}>
        <AppShell>{children}</AppShell>
      </SampleClockProvider>
    </AlertsProvider>
  );
}
