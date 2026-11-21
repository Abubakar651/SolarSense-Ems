import type { Metadata } from 'next';
import { SettingsView } from '@/features/settings/components/settings-view';
import { overnightLoadKw } from '@/lib/backup-hours';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Settings' };

export default async function SettingsPage() {
  const { settings, tariff, energy } = getServices();
  const [data, peakWindows, plan] = await Promise.all([
    settings.getSettings(),
    tariff.getPeakWindows(),
    energy.getDayPlan(),
  ]);
  return (
    <SettingsView
      data={data}
      peakWindows={peakWindows}
      overnightLoadKw={plan.status === 'ready' ? overnightLoadKw(plan.plan) : null}
    />
  );
}
