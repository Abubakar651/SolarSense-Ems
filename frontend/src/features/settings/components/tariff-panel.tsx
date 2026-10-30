import { SettingsSelect, SettingsText } from './settings-fields';

const PLANS = ['Time-of-use (peak / off-peak)', 'Flat rate'] as const;

export function TariffPanel() {
  return (
    <div className="card">
      <h2 style={{ marginBottom: 4 }}>Electricity tariff</h2>
      <p className="muted small" style={{ marginBottom: 'var(--sp-4)' }}>
        LESCO A-1 time-of-use rates. Match these to your bill so savings are accurate.
      </p>
      <SettingsSelect id="t-plan" label="Plan" options={PLANS} />
      <div className="two">
        <SettingsText id="t-ps" label="Peak starts" type="time" />
        <SettingsText id="t-pe" label="Peak ends" type="time" />
      </div>
      <div className="two">
        <SettingsText id="t-p" label="Peak rate (PKR/kWh)" numeric inputMode="decimal" />
        <SettingsText id="t-o" label="Off-peak rate (PKR/kWh)" numeric inputMode="decimal" />
      </div>
      <SettingsText id="t-e" label="Export credit (PKR/kWh)" numeric inputMode="decimal" />
    </div>
  );
}
