'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { PageHeader } from '@/components/ui/page-header';
import { Tabs } from '@/components/ui/tabs';
import { useToast } from '@/providers/toast-provider';
import type { SettingsData } from '@/types/domain/settings';
import { blackoutsEqual, isDirty, toFormValues, type SettingsValue } from '../view-model';
import { BatteryPanel } from './battery-panel';
import { DeleteAccountDialog } from './delete-account-dialog';
import { NotificationsPanel } from './notifications-panel';
import { ProfilePanel } from './profile-panel';
import { SaveBar } from './save-bar';
import { SecurityPanel } from './security-panel';
import { SettingsFormProvider } from './settings-form';
import { SitePanel } from './site-panel';
import { TariffPanel } from './tariff-panel';

export function SettingsView({ data }: { data: SettingsData }) {
  const router = useRouter();
  const toast = useToast();
  const [saved, setSaved] = useState(() => toFormValues(data));
  const [values, setValues] = useState(saved);
  const [savedBlackouts, setSavedBlackouts] = useState(data.blackouts);
  const [blackouts, setBlackouts] = useState(savedBlackouts);
  const [deleting, setDeleting] = useState(false);

  const set = useCallback(
    (key: string, value: SettingsValue) => setValues((current) => ({ ...current, [key]: value })),
    [],
  );

  const tabs = [
    {
      key: 'profile',
      label: 'Profile',
      content: <ProfilePanel profile={data.profile} onRequestDelete={() => setDeleting(true)} />,
    },
    { key: 'site', label: 'Site & hardware', content: <SitePanel site={data.site} /> },
    {
      key: 'battery',
      label: 'Battery control',
      content: (
        <BatteryPanel
          capacityKwh={data.battery.capacityKwh}
          blackouts={blackouts}
          onBlackoutsChange={setBlackouts}
        />
      ),
    },
    { key: 'tariff', label: 'Tariff', content: <TariffPanel /> },
    {
      key: 'notify',
      label: 'Notifications',
      content: <NotificationsPanel notifications={data.notifications} />,
    },
    { key: 'security', label: 'Security', content: <SecurityPanel /> },
  ];

  return (
    <section data-route="settings">
      <PageHeader title="Settings">
        Manage your account, system and how SolarSense behaves.
      </PageHeader>
      <SettingsFormProvider value={{ values, set }}>
        <Tabs id="setTabs" panelsId="setPanels" ariaLabel="Settings sections" tabs={tabs} />
      </SettingsFormProvider>
      <SaveBar
        dirty={isDirty(values, saved) || !blackoutsEqual(blackouts, savedBlackouts)}
        onSave={() => {
          setSaved(values);
          setSavedBlackouts(blackouts);
        }}
        onDiscard={() => {
          setValues(saved);
          setBlackouts(savedBlackouts);
          toast('Changes discarded');
        }}
      />
      <DeleteAccountDialog
        open={deleting}
        onClose={() => setDeleting(false)}
        onConfirm={() => {
          setDeleting(false);
          toast('Account deletion requested');
          router.push('/login');
        }}
      />
    </section>
  );
}
