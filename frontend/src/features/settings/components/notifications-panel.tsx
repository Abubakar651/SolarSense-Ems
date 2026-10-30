import { DataTable } from '@/components/ui/data-table';
import type { SettingsData } from '@/types/domain/settings';
import { SettingsSwitch } from './settings-fields';

const COLUMNS = [
  { label: 'Alert' },
  { label: 'In app', right: true },
  { label: 'Email', right: true },
];

export function NotificationsPanel({
  notifications,
}: {
  notifications: SettingsData['notifications'];
}) {
  return (
    <div className="card">
      <h2 style={{ marginBottom: 'var(--sp-3)' }}>Notifications</h2>
      <DataTable
        columns={COLUMNS}
        rows={notifications.map(({ label }, index) => [
          label,
          <SettingsSwitch
            key="app"
            settingKey={`notify-${index}-app`}
            label={`${label}, in app`}
          />,
          <SettingsSwitch
            key="email"
            settingKey={`notify-${index}-email`}
            label={`${label}, email`}
          />,
        ])}
      />
    </div>
  );
}
