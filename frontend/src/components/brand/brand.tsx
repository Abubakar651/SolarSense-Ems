import Link from 'next/link';
import type { CSSProperties } from 'react';
import { cn } from '@/lib/cn';
import { LogoMark } from './logo-mark';

interface BrandProps {
  href: string;
  /** Hide the wordmark on the smallest screens, leaving only the mark. */
  hideWordmarkOnXs?: boolean;
  style?: CSSProperties;
}

export function Brand({ href, hideWordmarkOnXs = false, style }: BrandProps) {
  return (
    <Link className="brand" href={href} style={style}>
      <LogoMark />
      <span className={cn(hideWordmarkOnXs && 'hide-xs', 'wm')}>
        Solar<span>Sense</span>
      </span>
    </Link>
  );
}
