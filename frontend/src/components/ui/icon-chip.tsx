import type { CSSProperties } from 'react';
import { cn } from '@/lib/cn';
import { Icon } from './icon';
import type { IconName } from './icon-paths';

interface IconChipProps {
  icon: IconName;
  tone?: 'warn' | 'crit' | 'info' | 'ok';
  /** Hide from assistive tech when the chip only decorates adjacent text. */
  decorative?: boolean;
  style?: CSSProperties;
}

/** Small rounded tile holding an icon, tinted by tone. */
export function IconChip({ icon, tone, decorative = false, style }: IconChipProps) {
  return (
    <span className={cn('ico-chip', tone)} aria-hidden={decorative || undefined} style={style}>
      <Icon name={icon} />
    </span>
  );
}
