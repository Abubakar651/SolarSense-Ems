'use client';

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { Icon } from '@/components/ui/icon';
import { cn } from '@/lib/cn';

interface ToastItem {
  id: number;
  message: string;
  leaving: boolean;
}

const VISIBLE_MS = 3700;
const FADE_MS = 300;

const ToastContext = createContext<((message: string) => void) | null>(null);

/** Provides `useToast()` and renders the polite live region that holds the toasts. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const toast = useCallback((message: string) => {
    const id = nextId.current++;
    setItems((current) => [...current, { id, message, leaving: false }]);
    window.setTimeout(
      () =>
        setItems((current) =>
          current.map((item) => (item.id === id ? { ...item, leaving: true } : item)),
        ),
      VISIBLE_MS,
    );
    window.setTimeout(
      () => setItems((current) => current.filter((item) => item.id !== id)),
      VISIBLE_MS + FADE_MS,
    );
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-wrap" id="toasts" role="status" aria-live="polite">
        {items.map(({ id, message, leaving }) => (
          <div key={id} className={cn('toast', leaving && 'out')}>
            <Icon name="check" />
            <span>{message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): (message: string) => void {
  const toast = useContext(ToastContext);
  if (!toast) throw new Error('useToast must be used inside <ToastProvider>');
  return toast;
}
