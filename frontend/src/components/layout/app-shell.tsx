'use client';

import { useState, type ReactNode } from 'react';
import { Sidebar } from './sidebar';
import { Topbar } from './topbar';

/** Authenticated app frame: sidebar (drawer below 1024px), sticky top bar and the page. */
export function AppShell({ children }: { children: ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const close = () => setDrawerOpen(false);

  return (
    <div id="app" data-layout="app">
      <Sidebar open={drawerOpen} onClose={close} />
      <div className="overlay" id="overlay" hidden={!drawerOpen} onClick={close} />
      <div className="main-col">
        <Topbar drawerOpen={drawerOpen} onMenu={() => setDrawerOpen((open) => !open)} />
        <main id="main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
