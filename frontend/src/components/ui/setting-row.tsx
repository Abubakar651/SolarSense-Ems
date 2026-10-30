import type { ReactNode } from 'react';

interface SettingRowProps {
  title: string;
  description?: string;
  /** The control on the right, usually a <Switch>. */
  children: ReactNode;
}

export function SettingRow({ title, description, children }: SettingRowProps) {
  return (
    <div className="setting">
      <div>
        <div className="t">{title}</div>
        {description && <p className="small muted">{description}</p>}
      </div>
      {children}
    </div>
  );
}
