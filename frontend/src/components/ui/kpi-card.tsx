import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';
import { Icon } from './icon';
import type { IconName } from './icon-paths';

interface KpiCardProps {
  label: string;
  icon?: IconName;
  /** Colours the value with the brand colour (one lead metric per strip). */
  lead?: boolean;
  /** The big number, usually a `<CountUp>` followed by a `<small>` unit. */
  value: ReactNode;
  sub?: ReactNode;
  subId?: string;
  /** Skip tabular numerals, e.g. when the value is a badge. */
  plain?: boolean;
}

export function KpiCard({ label, icon, lead, value, sub, subId, plain }: KpiCardProps) {
  return (
    <div className="card kpi">
      <div className="label">
        {icon && (
          <span className="ic">
            <Icon name={icon} />
          </span>
        )}
        {label}
      </div>
      <div className={cn('val', !plain && 'num', lead && 'pri')}>{value}</div>
      {sub !== undefined && (
        <div className="sub" id={subId}>
          {sub}
        </div>
      )}
    </div>
  );
}

/** Joined row of KPI cards (the `g-kpi` strip). */
export function KpiStrip({ children }: { children: ReactNode }) {
  return <div className="g-kpi grid">{children}</div>;
}
