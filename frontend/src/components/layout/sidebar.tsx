'use client';

import { useRef } from 'react';
import { Brand } from '@/components/brand/brand';
import { useFocusTrap } from '@/hooks/use-focus-trap';
import { cn } from '@/lib/cn';
import { SidebarNav } from './sidebar-nav';

interface SidebarProps {
  /** Mobile drawer state; the sidebar is always visible from 1024px. */
  open: boolean;
  onClose: () => void;
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const ref = useRef<HTMLElement>(null);
  useFocusTrap(ref, open, onClose);

  return (
    <aside className={cn('sidebar', open && 'open')} id="sidebar" aria-label="Sidebar" ref={ref}>
      <Brand href="/dashboard" />
      <SidebarNav onNavigate={onClose} />
    </aside>
  );
}
