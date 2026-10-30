import type { InputHTMLAttributes } from 'react';

type SwitchProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'aria-label'> & {
  /** Required: the switch has no visible text of its own. */
  'aria-label': string;
};

/** On/off toggle drawn with CSS around a native checkbox (keyboard and screen-reader friendly). */
export function Switch(props: SwitchProps) {
  return (
    <label className="switch">
      <input type="checkbox" {...props} />
      <span />
    </label>
  );
}
