import type { ReactNode } from 'react';
import { ToastProvider } from './toast-provider';

export function AppProviders({ children }: { children: ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
