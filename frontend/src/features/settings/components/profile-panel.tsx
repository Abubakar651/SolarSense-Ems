import { SettingRow } from '@/components/ui/setting-row';
import { ToastButton } from '@/components/ui/toast-button';
import type { SettingsData } from '@/types/domain/settings';
import { SettingsText } from './settings-fields';

interface ProfilePanelProps {
  profile: SettingsData['profile'];
  onRequestDelete: () => void;
}

export function ProfilePanel({ profile, onRequestDelete }: ProfilePanelProps) {
  return (
    <>
      <div className="card">
        <h2 style={{ marginBottom: 'var(--sp-4)' }}>Your profile</h2>
        <div className="row" style={{ marginBottom: 'var(--sp-5)' }}>
          <span
            className="avatar"
            style={{ width: 56, height: 56, fontSize: '1.125rem' }}
            aria-hidden="true"
          >
            {profile.initials}
          </span>
          <div>
            <b>{profile.name}</b>
            <p className="small muted">{profile.email}</p>
          </div>
        </div>
        <div className="two">
          <SettingsText id="p-name" label="Full name" autoComplete="name" />
          <SettingsText
            id="p-phone"
            label="Phone (optional)"
            type="tel"
            autoComplete="tel"
            hint="Used only for account recovery and critical alerts."
          />
        </div>
        <div className="field">
          <label htmlFor="p-email">Email</label>
          <div className="row" style={{ flexWrap: 'nowrap' }}>
            <input
              className="input"
              id="p-email"
              value={profile.email}
              readOnly
              aria-describedby="p-email-h"
            />
            <ToastButton
              className="btn btn-secondary"
              message="We'd send a confirmation link to both addresses."
            >
              Change
            </ToastButton>
          </div>
          <p className="hint" id="p-email-h">
            Changing your email requires confirming a link we send to the new address.
          </p>
        </div>
      </div>
      <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
        <h2 style={{ color: 'var(--bad)' }}>Danger zone</h2>
        <SettingRow
          title="Download my data"
          description="A copy of your profile, site settings and history."
        >
          <ToastButton
            className="btn btn-secondary btn-sm"
            message="Export requested. We'll email a download link."
          >
            Request export
          </ToastButton>
        </SettingRow>
        <SettingRow
          title="Delete account"
          description="Permanently removes your account and all data. This cannot be undone."
        >
          <button
            className="btn btn-outline-danger btn-sm"
            type="button"
            id="delBtn"
            onClick={onRequestDelete}
          >
            Delete account
          </button>
        </SettingRow>
      </div>
    </>
  );
}
