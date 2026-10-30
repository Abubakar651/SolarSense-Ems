'use client';

import Link from 'next/link';
import { useCallback, useRef, useState, type MouseEvent } from 'react';
import { Brand } from '@/components/brand/brand';
import { Icon } from '@/components/ui/icon';
import { useFocusTrap } from '@/hooks/use-focus-trap';
import { useScrollSpy } from '@/hooks/use-scroll-spy';
import { useScrolled } from '@/hooks/use-scrolled';
import { cn } from '@/lib/cn';
import { scrollToSection } from '@/lib/scroll';
import { SECTION_IDS, SECTION_LINKS } from '../content';

/** Sticky landing header with scroll-spy links and a focus-trapped menu drawer below 1024px. */
export function LandingNav() {
  const scrolled = useScrolled();
  const active = useScrollSpy(SECTION_IDS);
  const [open, setOpen] = useState(false);
  const drawerRef = useRef<HTMLElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useFocusTrap(drawerRef, open, close);

  const goTo = (id: string) => (event: MouseEvent) => {
    event.preventDefault();
    close();
    scrollToSection(id);
  };

  return (
    <>
      <header className={cn('land-nav', scrolled && 'scrolled')}>
        <div className="wrap">
          <Brand href="/" style={{ padding: 0 }} />
          <nav className="land-links" id="landLinks" aria-label="Page sections">
            {SECTION_LINKS.map(({ id, label }) => (
              <a
                key={id}
                href={`#${id}`}
                aria-current={active === id ? 'true' : undefined}
                onClick={goTo(id)}
              >
                {label}
              </a>
            ))}
          </nav>
          <div className="push row">
            <Link className="btn btn-secondary btn-sm hide-xs" href="/login">
              Log in
            </Link>
            <Link className="btn btn-primary btn-sm" href="/signup">
              Get started
            </Link>
            <button
              className="icon-btn"
              id="landMenuBtn"
              type="button"
              aria-label="Open menu"
              aria-expanded={open}
              aria-controls="landDrawer"
              onClick={() => setOpen(true)}
            >
              <Icon name="menu" />
            </button>
          </div>
        </div>
      </header>
      <div className="land-scrim" id="landScrim" hidden={!open} onClick={close} />
      <aside
        className={cn('land-drawer', open && 'open')}
        id="landDrawer"
        role="dialog"
        aria-modal="true"
        aria-label="Menu"
        ref={drawerRef}
      >
        <div className="head">
          <Brand href="/" style={{ padding: 0 }} />
          <button
            className="icon-btn"
            id="landCloseBtn"
            type="button"
            aria-label="Close menu"
            onClick={close}
          >
            <Icon name="x" />
          </button>
        </div>
        {SECTION_LINKS.map(({ id, label }) => (
          <a key={id} href={`#${id}`} onClick={goTo(id)}>
            {label}
          </a>
        ))}
        <div className="foot">
          <Link className="btn btn-secondary btn-block" href="/login">
            Log in
          </Link>
          <Link className="btn btn-primary btn-block" href="/signup">
            Get started
          </Link>
        </div>
      </aside>
    </>
  );
}
