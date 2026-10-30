'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icon } from '@/components/ui/icon';
import { titleForPath } from '@/config/nav';
import { useScrolled } from '@/hooks/use-scrolled';
import { cn } from '@/lib/cn';
import { useAlerts } from '@/providers/alerts-provider';
import { UserMenu } from './user-menu';

interface TopbarProps {
  drawerOpen: boolean;
  onMenu: () => void;
}

const BELL_BADGE_STYLE = {
  position: 'absolute',
  top: 6,
  right: 6,
  background: 'var(--bad)',
  color: '#fff',
  borderRadius: 99,
  fontSize: '.6875rem',
  minWidth: 18,
  height: 18,
  display: 'grid',
  placeItems: 'center',
  fontWeight: 700,
} as const;

export function Topbar({ drawerOpen, onMenu }: TopbarProps) {
  const pathname = usePathname();
  const scrolled = useScrolled();
  const { unreadCount } = useAlerts();

  return (
    <header className={cn('topbar', scrolled && 'scrolled')}>
      <button
        className="icon-btn"
        id="menuBtn"
        aria-label="Open menu"
        aria-expanded={drawerOpen}
        aria-controls="sidebar"
        onClick={onMenu}
      >
        <Icon name="menu" />
      </button>
      <h2 id="topTitle">{titleForPath(pathname)}</h2>
      <span
        className="badge b-warn hide-xs"
        title="Figures are replayed from recorded data of station LHR-RES-01, not live"
      >
        <Icon name="info" style={{ width: 14, height: 14 }} />
        Sample data
      </span>
      <Link
        className="icon-btn"
        href="/alerts"
        aria-label={unreadCount ? `Alerts, ${unreadCount} unread` : 'Alerts'}
        style={{ position: 'relative' }}
      >
        <Icon name="bell" />
        {unreadCount > 0 && <span style={BELL_BADGE_STYLE}>{unreadCount}</span>}
      </Link>
      <UserMenu />
    </header>
  );
}
