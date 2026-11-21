'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { Icon } from '@/components/ui/icon';
import type { AccountUser } from '@/types/domain/account';

/** Avatar button with the account dropdown; closes on outside click and Escape. */
interface UserMenuProps {
  user: AccountUser;
  /** Server action that ends the session and returns to /login. */
  logout: () => Promise<void>;
}

export function UserMenu({ user, logout }: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <div className="menu-wrap" ref={wrapRef}>
      <button
        className="icon-btn"
        id="userBtn"
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={`${user.name}, account menu`}
        style={{ width: 'auto', padding: '0 4px' }}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="avatar" aria-hidden="true">
          {user.initials}
        </span>
      </button>
      <div className="menu" id="userMenu" hidden={!open}>
        <div style={{ padding: '8px 12px' }}>
          <b>{user.name}</b>
          <p className="xs muted">{user.email}</p>
        </div>
        <hr />
        <Link href="/settings" onClick={close}>
          <Icon name="user" />
          Profile &amp; settings
        </Link>
        <hr />
        <form action={logout}>
          <button type="submit" onClick={close}>
            <Icon name="logout" />
            Log out
          </button>
        </form>
      </div>
    </div>
  );
}
