import type { CSSProperties } from 'react';
import { cn } from '@/lib/cn';
import { ICON_PATHS, type IconName } from './icon-paths';

interface IconProps {
  name: IconName;
  /** `lg` renders the 24px variant. */
  size?: 'md' | 'lg';
  className?: string;
  style?: CSSProperties;
}

/** Decorative stroke icon; the markup comes from the constant ICON_PATHS map. */
export function Icon({ name, size = 'md', className, style }: IconProps) {
  return (
    <svg
      className={cn('i', size === 'lg' && 'lg', className)}
      style={style}
      viewBox="0 0 24 24"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: ICON_PATHS[name] }}
    />
  );
}
