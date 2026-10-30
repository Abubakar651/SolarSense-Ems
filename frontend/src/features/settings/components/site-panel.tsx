import { ToastButton } from '@/components/ui/toast-button';
import type { SettingsData } from '@/types/domain/settings';
import { SettingsSelect, SettingsText } from './settings-fields';

const INVERTERS = ['GoodWe', 'Other'] as const;

export function SitePanel({ site }: { site: SettingsData['site'] }) {
  return (
    <div className="card">
      <div className="card-h">
        <div>
          <h2>Site</h2>
        </div>
        <span className="badge b-neutral">{site.syncStatus}</span>
      </div>
      <div className="two">
        <SettingsText id="s-name" label="Site name" />
        <SettingsText id="s-city" label="City" placeholder="Your city" />
      </div>
      <SettingsText id="s-addr" label="Address" autoComplete="street-address" />
      <h2 style={{ margin: 'var(--sp-5) 0 var(--sp-2)' }}>Hardware</h2>
      <div className="note" role="note">
        Hardware sizes drive your forecasts and battery plan. Only change them if you&apos;ve added
        or replaced equipment.
      </div>
      <div className="two">
        <SettingsText id="s-pv" label="Solar capacity (kWp)" numeric inputMode="decimal" />
        <SettingsText id="s-bat" label="Battery capacity (kWh)" numeric inputMode="decimal" />
      </div>
      <div className="two">
        <SettingsSelect id="s-inv" label="Inverter" options={INVERTERS} />
        <div className="field">
          <label htmlFor="s-sn">Serial number</label>
          <input className="input" id="s-sn" value={site.serial} readOnly />
        </div>
      </div>
      <ToastButton className="btn btn-secondary" message="Reconnecting to inverter…">
        Reconnect inverter
      </ToastButton>
    </div>
  );
}
