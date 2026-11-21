'use client';

import { useState, type ReactNode } from 'react';
import type { AccountUser } from '@/types/domain/account';
import { Sidebar } from './sidebar';
import { Topbar } from './topbar';

interface AppShellProps {
  children: ReactNode;
  user: AccountUser;
  /** True while the screens replay recorded sample data, which the top bar says so. */
  sample: boolean;
  /** Server action that ends the session. */
  logout: () => Promise<void>;
}

/** Authenticated app frame: sidebar (drawer below 1024px), sticky top bar and the page. */
export function AppShell({ children, user, sample, logout }: AppShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const close = () => setDrawerOpen(false);

  return (
    <div id="app" data-layout="app">
      <Sidebar open={drawerOpen} onClose={close} />
      <div className="overlay" id="overlay" hidden={!drawerOpen} onClick={close} />
      <div className="main-col">
        <Topbar
          drawerOpen={drawerOpen}
          onMenu={() => setDrawerOpen((open) => !open)}
          user={user}
          sample={sample}
          logout={logout}
        />
        <main id="main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
