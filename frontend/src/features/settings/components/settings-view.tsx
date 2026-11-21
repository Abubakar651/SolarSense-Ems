'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useState } from 'react';
import { PageHeader } from '@/components/ui/page-header';
import { Tabs } from '@/components/ui/tabs';
import { useToast } from '@/providers/toast-provider';
import type { PeakWindow } from '@/lib/tariff';
import type { SettingsData } from '@/types/domain/settings';
import { changePasswordAction, deleteAccountAction, saveSettingsAction } from '../actions';
import {
  blackoutsEqual,
  isDirty,
  toFormValues,
  toSettingsUpdate,
  type SettingsValue,
} from '../view-model';
import { BatteryPanel } from './battery-panel';
import { DeleteAccountDialog } from './delete-account-dialog';
import { NotificationsPanel } from './notifications-panel';
import { ProfilePanel } from './profile-panel';
import { SaveBar } from './save-bar';
import { SecurityPanel } from './security-panel';
import { SettingsFormProvider } from './settings-form';
import { SitePanel } from './site-panel';
import { TariffPanel } from './tariff-panel';

export function SettingsView({
  data,
  peakWindows,
  overnightLoadKw,
}: {
  data: SettingsData;
  /** The home's mean overnight usage from today's plan; null while there is no plan. */
  overnightLoadKw: number | null;
  /** LESCO's seasonal peak hours, from the tariff repository (the backend's tariff engine when live). */
  peakWindows: readonly PeakWindow[];
}) {
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
          overnightLoadKw={overnightLoadKw}
          blackouts={blackouts}
          onBlackoutsChange={setBlackouts}
        />
      ),
    },
    { key: 'tariff', label: 'Tariff', content: <TariffPanel peakWindows={peakWindows} /> },
    {
      key: 'notify',
      label: 'Notifications',
      content: <NotificationsPanel notifications={data.notifications} />,
    },
    {
      key: 'security',
      label: 'Security',
      content: <SecurityPanel changePassword={changePasswordAction} />,
    },
  ];

  return (
    <section data-route="settings">
      <PageHeader title="Settings" />
      <SettingsFormProvider value={{ values, set }}>
        <Tabs id="setTabs" panelsId="setPanels" ariaLabel="Settings sections" tabs={tabs} />
      </SettingsFormProvider>
      <SaveBar
        dirty={isDirty(values, saved) || !blackoutsEqual(blackouts, savedBlackouts)}
        onSave={async () => {
          const result = await saveSettingsAction(
            toSettingsUpdate(values, blackouts, data.notifications),
          );
          if (!result.ok) {
            toast(result.error);
            return false;
          }
          setSaved(values);
          setSavedBlackouts(blackouts);
          return true;
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
        onConfirm={async (password) => {
          const result = await deleteAccountAction(password);
          if (!result.ok) {
            toast(result.error);
            return;
          }
          setDeleting(false);
          toast('Your account has been deleted');
          router.push('/login');
        }}
      />
    </section>
  );
}
