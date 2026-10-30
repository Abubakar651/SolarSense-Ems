import { SettingRow } from '@/components/ui/setting-row';
import { Switch } from '@/components/ui/switch';

export function EmailReportsCard() {
  return (
    <div className="card" style={{ alignSelf: 'start' }}>
      <h2 style={{ marginBottom: 'var(--sp-3)' }}>Email reports</h2>
      <SettingRow title="Monthly summary" description="Sent on the 1st of each month">
        <Switch defaultChecked aria-label="Monthly summary email" />
      </SettingRow>
      <SettingRow title="Weekly digest" description="Every Monday morning">
        <Switch aria-label="Weekly digest email" />
      </SettingRow>
      <div className="field" style={{ margin: 'var(--sp-3) 0 0' }}>
        <label htmlFor="rep-to">Send to</label>
        <input
          className="input"
          id="rep-to"
          defaultValue="zaeem@example.com"
          type="email"
          autoComplete="email"
        />
      </div>
    </div>
  );
}
