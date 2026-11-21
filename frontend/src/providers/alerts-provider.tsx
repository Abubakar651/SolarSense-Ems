'use client';

import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { Alert } from '@/types/domain/alerts';

interface AlertsContextValue {
  alerts: Alert[];
  unreadCount: number;
  /** Marks every alert read here and on the server; resolves false (and changes nothing) if saving failed. */
  markAllRead: () => Promise<boolean>;
  /** Marks one alert read here and on the server; resolves false (and changes nothing) if saving failed. */
  markOneRead: (id: string) => Promise<boolean>;
}

const AlertsContext = createContext<AlertsContextValue | null>(null);

/**
 * Single source of truth for alert read-state: the sidebar badge, the bell and the alerts list
 * all read from here, so "Mark all as read" updates them together.
 */
interface AlertsProviderProps {
  initial: Alert[];
  /** Server action that stores "all read"; resolves whether it succeeded. */
  persistReadAll: () => Promise<{ ok: boolean }>;
  /** Server action that stores one alert read; resolves whether it succeeded. */
  persistReadOne: (id: string) => Promise<{ ok: boolean }>;
  children: ReactNode;
}

export function AlertsProvider({
  initial,
  persistReadAll,
  persistReadOne,
  children,
}: AlertsProviderProps) {
  const [alerts, setAlerts] = useState(initial);
  const value = useMemo<AlertsContextValue>(
    () => ({
      alerts,
      unreadCount: alerts.filter((alert) => alert.unread).length,
      markAllRead: async () => {
        const { ok } = await persistReadAll();
        if (ok) setAlerts((current) => current.map((alert) => ({ ...alert, unread: false })));
        return ok;
      },
      markOneRead: async (id: string) => {
        const { ok } = await persistReadOne(id);
        if (ok) {
          setAlerts((current) =>
            current.map((alert) => (alert.id === id ? { ...alert, unread: false } : alert)),
          );
        }
        return ok;
      },
    }),
    [alerts, persistReadAll, persistReadOne],
  );
  return <AlertsContext.Provider value={value}>{children}</AlertsContext.Provider>;
}

export function useAlerts(): AlertsContextValue {
  const value = useContext(AlertsContext);
  if (!value) throw new Error('useAlerts must be used inside <AlertsProvider>');
  return value;
}
