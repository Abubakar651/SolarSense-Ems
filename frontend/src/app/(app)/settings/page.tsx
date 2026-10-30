import type { Metadata } from 'next';
import { SettingsView } from '@/features/settings/components/settings-view';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Settings' };

export default async function SettingsPage() {
  const data = await getServices().settings.getSettings();
  return <SettingsView data={data} />;
}
