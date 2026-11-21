'use client';

import { useState } from 'react';
import { SettingRow } from '@/components/ui/setting-row';
import { Switch } from '@/components/ui/switch';
import { useToast } from '@/providers/toast-provider';
import type { ReportEmailPrefs } from '@/types/domain/reports';
import { saveReportPrefsAction } from '../actions';

export function EmailReportsCard({ initial }: { initial: ReportEmailPrefs }) {
  const toast = useToast();
  const [prefs, setPrefs] = useState(initial);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    const result = await saveReportPrefsAction(prefs);
    setSaving(false);
    toast(result.ok ? 'Email report settings saved' : result.error);
  };

  return (
    <div className="card" style={{ alignSelf: 'start' }}>
      <h2 style={{ marginBottom: 'var(--sp-3)' }}>Email reports</h2>
      <SettingRow title="Monthly summary" description="Sent on the 1st of each month">
        <Switch
          checked={prefs.monthly}
          onChange={(event) => setPrefs({ ...prefs, monthly: event.target.checked })}
          aria-label="Monthly summary email"
        />
      </SettingRow>
      <SettingRow title="Weekly digest" description="Every Monday morning">
        <Switch
          checked={prefs.weekly}
          onChange={(event) => setPrefs({ ...prefs, weekly: event.target.checked })}
          aria-label="Weekly digest email"
        />
      </SettingRow>
      <div className="field" style={{ margin: 'var(--sp-3) 0 0' }}>
        <label htmlFor="rep-to">Send to</label>
        <input
          className="input"
          id="rep-to"
          value={prefs.sendTo}
          onChange={(event) => setPrefs({ ...prefs, sendTo: event.target.value })}
          type="email"
          autoComplete="email"
        />
      </div>
      <button
        className="btn btn-secondary btn-sm"
        type="button"
        id="rep-save"
        style={{ marginTop: 'var(--sp-3)' }}
        disabled={saving}
        onClick={() => void save()}
      >
        Save email settings
      </button>
    </div>
  );
}
