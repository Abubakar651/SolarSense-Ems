import type { ReactNode } from 'react';
import { PublicShell } from '@/components/layout/public-shell';

export default function MarketingLayout({ children }: { children: ReactNode }) {
  return <PublicShell layout="landing">{children}</PublicShell>;
}
