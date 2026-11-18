import { ChoiceGroup, type ChoiceOption } from '@/components/ui/choice-group';
import { SettingRow } from '@/components/ui/setting-row';
import { MIN_RESERVE_PCT } from '@/lib/tariff';
import type { BlackoutWindow } from '@/types/domain/settings';
import { reserveHint } from '../view-model';
import { BlackoutCard } from './blackout-card';
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

/** Rules the planner always follows (AGENTS.md physical laws 2 and 4, BESSConfig.min_soc_pct). */
const FIXED_RULES = [
  {
    title: 'Never charge from the grid at peak rates',
    description: 'During peak hours the battery charges from solar only.',
  },
  {
    title: `Always keep ${MIN_RESERVE_PCT}% in the battery`,
    description: 'The inverter does not discharge below this emergency level.',
  },
  {
    title: 'No export during an outage',
    description: 'The inverter never feeds power into a grid that is down.',
  },
] as const;

interface BatteryPanelProps {
  capacityKwh: number;
  blackouts: readonly BlackoutWindow[];
  onBlackoutsChange: (blackouts: BlackoutWindow[]) => void;
}

export function BatteryPanel({ capacityKwh, blackouts, onBlackoutsChange }: BatteryPanelProps) {
  const [reserve, setReserve] = useTextSetting('reserve');

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
            min={MIN_RESERVE_PCT}
            max="100"
            step="5"
            value={reserve}
            onChange={(event) => setReserve(event.target.value)}
            aria-describedby="reserve-h"
          />
          <div className="row between xs faint">
            <span>{`${MIN_RESERVE_PCT}% · inverter minimum`}</span>
            <span>100% · max backup</span>
          </div>
          <p className="hint" id="reserve-h" aria-live="polite" style={{ marginTop: 6 }}>
            {reserveHint(Number(reserve), capacityKwh)}
          </p>
        </div>
      </div>
      <BlackoutCard blackouts={blackouts} onChange={onBlackoutsChange} />
      <div className="card">
        <h2>Fixed rules</h2>
        <p className="muted small">
          The planner always follows these. They cannot be switched off.
        </p>
        {FIXED_RULES.map(({ title, description }) => (
          <SettingRow key={title} title={title} description={description}>
            <span className="badge b-ok">Always on</span>
          </SettingRow>
        ))}
      </div>
    </div>
  );
}
