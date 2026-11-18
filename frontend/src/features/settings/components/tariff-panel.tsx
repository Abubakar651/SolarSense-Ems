import { SettingRow } from '@/components/ui/setting-row';
import { pad } from '@/lib/format';
import {
  PROSUMER_REGIMES,
  SEASONAL_PEAK_WINDOWS,
  TARIFF_CATEGORIES,
  TOU_RATES,
  regimeInfo,
  type ProsumerRegime,
} from '@/lib/tariff';
import { SettingsSelect, SettingsSwitch, SettingsText } from './settings-fields';
import { useTextSetting } from './settings-form';

const CATEGORY_OPTIONS = TARIFF_CATEGORIES.map(({ id, label }) => ({ value: id, label }));
const REGIME_OPTIONS = PROSUMER_REGIMES.map(({ id, label }) => ({ value: id, label }));

const hours = (start: number, end: number) => `${pad(start)}:00 – ${pad(end)}:00`;

export function TariffPanel() {
  const [regimeId] = useTextSetting('t-reg');
  const regime = regimeInfo(regimeId as ProsumerRegime);

  return (
    <div className="grid">
      <div className="card">
        <h2 style={{ marginBottom: 4 }}>Electricity tariff</h2>
        <p className="muted small" style={{ marginBottom: 'var(--sp-4)' }}>
          Your LESCO connection, as it appears on your bill. These are the options the planner
          understands.
        </p>
        <SettingsSelect id="t-cat" label="Tariff category" options={CATEGORY_OPTIONS} />
        <SettingsSelect
          id="t-reg"
          label="Solar export arrangement"
          options={REGIME_OPTIONS}
          hint={regime.summary}
        />
        <SettingsText
          id="t-load"
          label="Sanctioned load (kW)"
          numeric
          inputMode="decimal"
          hint="Shown on your bill. Fixed charges are billed per kW."
        />
        <SettingRow
          title="Active taxpayer (ATL filer)"
          description="Affects the income tax withheld on your bill."
        >
          <SettingsSwitch settingKey="t-atl" label="Active taxpayer" />
        </SettingRow>
        <SettingRow
          title="Include electricity duty"
          description="Adds the 1.5% duty to bill estimates."
        >
          <SettingsSwitch settingKey="t-duty" label="Include electricity duty" />
        </SettingRow>
        <SettingRow
          title="Protected consumer"
          description="Stay under 200 units a month to keep the lower protected slab rates."
        >
          <SettingsSwitch settingKey="t-prot" label="Protected consumer" />
        </SettingRow>
      </div>
      <div className="card">
        <h2 style={{ marginBottom: 4 }}>Set by LESCO</h2>
        <p className="muted small" style={{ marginBottom: 'var(--sp-4)' }}>
          The utility fixes these, so they cannot be edited here.
        </p>
        <div className="two">
          <div className="field">
            <label htmlFor="t-rate-peak">Peak rate (PKR/kWh)</label>
            <input
              className="input num"
              id="t-rate-peak"
              value={TOU_RATES.peakPkr.toFixed(2)}
              readOnly
            />
          </div>
          <div className="field">
            <label htmlFor="t-rate-off">Off-peak rate (PKR/kWh)</label>
            <input
              className="input num"
              id="t-rate-off"
              value={TOU_RATES.offPeakPkr.toFixed(2)}
              readOnly
              aria-describedby="t-rate-h"
            />
          </div>
        </div>
        <p className="hint" id="t-rate-h" style={{ marginBottom: 'var(--sp-4)' }}>
          Base rates. Your bill adds GST, the financing surcharge and fuel adjustments.
        </p>
        <div className="field">
          <label htmlFor="t-export">Export credit (PKR/kWh)</label>
          <input
            className="input num"
            id="t-export"
            value={regime.exportPkrPerKwh.toFixed(2)}
            readOnly
          />
          <p className="hint">Follows your export arrangement above.</p>
        </div>
        <h3 style={{ margin: 'var(--sp-4) 0 var(--sp-2)' }}>Peak hours by season</h3>
        {SEASONAL_PEAK_WINDOWS.map((window) => (
          <div className="row between small" key={window.season} style={{ padding: '6px 0' }}>
            <span>
              {window.season} <span className="faint">({monthRange(window.months)})</span>
            </span>
            <b className="num">{hours(window.startHour, window.endHour)}</b>
          </div>
        ))}
      </div>
    </div>
  );
}

const MONTH_NAMES = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

/** [12, 1, 2] -> "Dec–Feb". */
function monthRange(months: readonly number[]): string {
  const first = months[0] as number;
  const last = months[months.length - 1] as number;
  return `${MONTH_NAMES[first - 1]}–${MONTH_NAMES[last - 1]}`;
}
