import type { ReactNode } from 'react';
import { PublicShell } from '@/components/layout/public-shell';

export default function AuthGroupLayout({ children }: { children: ReactNode }) {
  return <PublicShell layout="auth">{children}</PublicShell>;
}
