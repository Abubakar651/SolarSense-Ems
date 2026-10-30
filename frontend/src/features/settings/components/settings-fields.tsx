'use client';

import type { CSSProperties, HTMLInputTypeAttribute } from 'react';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/cn';
import { useFlagSetting, useTextSetting } from './settings-form';

interface SettingsTextProps {
  id: string;
  label: string;
  type?: HTMLInputTypeAttribute;
  autoComplete?: string;
  inputMode?: 'decimal';
  /** Tabular figures, for numbers. */
  numeric?: boolean;
  placeholder?: string;
  hint?: string;
  fieldStyle?: CSSProperties;
}

/** Labelled text input bound to a setting of the same id. */
export function SettingsText({
  id,
  label,
  type,
  autoComplete,
  inputMode,
  numeric,
  placeholder,
  hint,
  fieldStyle,
}: SettingsTextProps) {
  const [value, setValue] = useTextSetting(id);

  return (
    <div className="field" style={fieldStyle}>
      <label htmlFor={id}>{label}</label>
      <input
        className={cn('input', numeric && 'num')}
        id={id}
        type={type}
        autoComplete={autoComplete}
        inputMode={inputMode}
        placeholder={placeholder}
        value={value}
        onChange={(event) => setValue(event.target.value)}
      />
      {hint && <p className="hint">{hint}</p>}
    </div>
  );
}

interface SettingsSelectProps {
  id: string;
  label: string;
  options: readonly string[];
}

export function SettingsSelect({ id, label, options }: SettingsSelectProps) {
  const [value, setValue] = useTextSetting(id);

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select
        className="input"
        id={id}
        value={value}
        onChange={(event) => setValue(event.target.value)}
      >
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </div>
  );
}

/** On/off toggle bound to a boolean setting. */
export function SettingsSwitch({ settingKey, label }: { settingKey: string; label: string }) {
  const [on, setOn] = useFlagSetting(settingKey);
  return (
    <Switch checked={on} onChange={(event) => setOn(event.target.checked)} aria-label={label} />
  );
}
