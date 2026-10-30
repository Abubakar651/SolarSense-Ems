'use client';

import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { Alert } from '@/types/domain/alerts';

interface AlertsContextValue {
  alerts: Alert[];
  unreadCount: number;
  markAllRead: () => void;
}

const AlertsContext = createContext<AlertsContextValue | null>(null);

/**
 * Single source of truth for alert read-state: the sidebar badge, the bell and the alerts list
 * all read from here, so "Mark all as read" updates them together.
 */
export function AlertsProvider({ initial, children }: { initial: Alert[]; children: ReactNode }) {
  const [alerts, setAlerts] = useState(initial);
  const value = useMemo<AlertsContextValue>(
    () => ({
      alerts,
      unreadCount: alerts.filter((alert) => alert.unread).length,
      markAllRead: () =>
        setAlerts((current) => current.map((alert) => ({ ...alert, unread: false }))),
    }),
    [alerts],
  );
  return <AlertsContext.Provider value={value}>{children}</AlertsContext.Provider>;
}

export function useAlerts(): AlertsContextValue {
  const value = useContext(AlertsContext);
  if (!value) throw new Error('useAlerts must be used inside <AlertsProvider>');
  return value;
}
