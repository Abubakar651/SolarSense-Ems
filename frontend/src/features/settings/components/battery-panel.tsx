import { ChoiceGroup, type ChoiceOption } from '@/components/ui/choice-group';
import { SettingRow } from '@/components/ui/setting-row';
import type { BlackoutWindow, PriorityMode } from '@/types/domain/settings';
import { reserveHint } from '../view-model';
import { BlackoutCard } from './blackout-card';
import { SettingsSwitch, SettingsText } from './settings-fields';
import { useTextSetting } from './settings-form';

const MODE_OPTIONS: ChoiceOption<'advise' | 'control'>[] = [
  {
    value: 'advise',
    title: 'Advise me',
    badge: { text: 'Available', tone: 'ok' },
    description: 'We show the plan; you apply it on your inverter app.',
  },
  {
    value: 'control',
    title: 'Control automatically',
    badge: { text: 'Coming soon', tone: 'neutral' },
    description:
      'SolarSense sends the plan to your inverter for you. You can still override it any time.',
    disabled: true,
  },
];

const PRIORITY_OPTIONS: ChoiceOption<PriorityMode>[] = [
  {
    value: 'comfort',
    title: 'Max backup',
    description: 'Prefer a fuller battery. Savings are lower but outages are covered longest.',
  },
  {
    value: 'balanced',
    title: 'Balanced',
    badge: { text: 'Recommended', tone: 'primary' },
    description: 'Plan around expected outages while still avoiding peak rates.',
  },
  {
    value: 'savings',
    title: 'Max savings',
    description:
      'Use the battery as much as possible. Higher chance it is low when an outage hits.',
  },
];

interface BatteryPanelProps {
  capacityKwh: number;
  blackouts: readonly BlackoutWindow[];
  onBlackoutsChange: (blackouts: BlackoutWindow[]) => void;
}

export function BatteryPanel({ capacityKwh, blackouts, onBlackoutsChange }: BatteryPanelProps) {
  const [reserve, setReserve] = useTextSetting('reserve');
  const [priority, setPriority] = useTextSetting('prio');

  return (
    <div className="grid">
      <div className="card">
        <h2 style={{ marginBottom: 4 }}>How should SolarSense act?</h2>
        <p className="muted small" style={{ marginBottom: 'var(--sp-4)' }}>
          Control of the inverter is being connected. Until then, plans are shown as
          recommendations.
        </p>
        <ChoiceGroup
          name="mode"
          ariaLabel="Control mode"
          options={MODE_OPTIONS}
          value="advise"
          onChange={() => undefined}
        />
      </div>
      <div className="card">
        <h2 style={{ marginBottom: 'var(--sp-4)' }}>Backup reserve</h2>
        <div className="field" style={{ marginBottom: 0 }}>
          <label htmlFor="reserve">
            Keep at least <b className="num" id="reserve-v">{`${reserve}%`}</b> in the battery for
            outages
          </label>
          <input
            type="range"
            id="reserve"
            min="10"
            max="100"
            step="5"
            value={reserve}
            onChange={(event) => setReserve(event.target.value)}
            aria-describedby="reserve-h"
          />
          <div className="row between xs faint">
            <span>10% · more savings</span>
            <span>100% · max backup</span>
          </div>
          <p className="hint" id="reserve-h" aria-live="polite" style={{ marginTop: 6 }}>
            {reserveHint(Number(reserve), capacityKwh)}
          </p>
        </div>
      </div>
      <BlackoutCard blackouts={blackouts} onChange={onBlackoutsChange} />
      <div className="card">
        <h2 style={{ marginBottom: 'var(--sp-3)' }}>Priority</h2>
        <ChoiceGroup
          name="prio"
          ariaLabel="Priority"
          options={PRIORITY_OPTIONS}
          value={priority as PriorityMode}
          onChange={setPriority}
        />
      </div>
      <div className="card">
        <h2>Rules</h2>
        <SettingRow
          title="Never charge from the grid at peak rates"
          description="The battery charges from solar during peak hours only."
        >
          <SettingsSwitch settingKey="rule-peak" label="Never charge from the grid at peak rates" />
        </SettingRow>
        <SettingRow
          title="Allow charging from the grid overnight"
          description="Useful on cloudy days when off-peak power is cheap."
        >
          <SettingsSwitch settingKey="rule-overnight" label="Allow overnight grid charging" />
        </SettingRow>
        <SettingRow
          title="Export extra solar to the grid"
          description="Earn the export credit when the battery is full."
        >
          <SettingsSwitch settingKey="rule-export" label="Export extra solar" />
        </SettingRow>
        <div className="two" style={{ marginTop: 'var(--sp-3)' }}>
          <SettingsText
            id="ch-from"
            label="Overnight charge window starts"
            type="time"
            fieldStyle={{ marginBottom: 0 }}
          />
          <SettingsText id="ch-to" label="Ends" type="time" fieldStyle={{ marginBottom: 0 }} />
        </div>
      </div>
    </div>
  );
}
