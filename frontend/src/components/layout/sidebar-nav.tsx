'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Fragment, useLayoutEffect, useRef } from 'react';
import { Icon } from '@/components/ui/icon';
import { APP_NAV } from '@/config/nav';
import { useAlerts } from '@/providers/alerts-provider';

const ALERTS_HREF = '/alerts';

/** Grouped app navigation with an indicator bar that slides to the current page. */
export function SidebarNav({ onNavigate }: { onNavigate: () => void }) {
  const pathname = usePathname();
  const { unreadCount } = useAlerts();
  const navRef = useRef<HTMLElement>(null);
  const indicatorRef = useRef<HTMLSpanElement>(null);
  const placed = useRef(false);

  useLayoutEffect(() => {
    const current = navRef.current?.querySelector<HTMLElement>('a[aria-current="page"]');
    const indicator = indicatorRef.current;
    if (!indicator) return;
    if (!current?.offsetHeight) {
      placed.current = false;
      indicator.style.opacity = '0';
      return;
    }
    // The first placement jumps; later ones slide.
    indicator.style.transition = placed.current ? '' : 'none';
    indicator.style.opacity = '1';
    indicator.style.transform = `translateY(${current.offsetTop + 10}px)`;
    indicator.style.height = `${current.offsetHeight - 20}px`;
    placed.current = true;
  }, [pathname]);

  return (
    <nav className="nav" id="nav" aria-label="Main" ref={navRef}>
      {APP_NAV.map((group) => (
        <Fragment key={group.label}>
          <div className="nav-sep">{group.label}</div>
          {group.items.map(({ href, label, icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? 'page' : undefined}
              onClick={onNavigate}
            >
              <Icon name={icon} />
              <span>{label}</span>
              {href === ALERTS_HREF && unreadCount > 0 && (
                <span className="badge b-bad count">{unreadCount}</span>
              )}
            </Link>
          ))}
        </Fragment>
      ))}
      <span className="nav-ind" aria-hidden="true" ref={indicatorRef} />
    </nav>
  );
}
