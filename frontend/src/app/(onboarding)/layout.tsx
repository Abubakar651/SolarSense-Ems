import type { ReactNode } from 'react';
import { PublicShell } from '@/components/layout/public-shell';

export default function OnboardingGroupLayout({ children }: { children: ReactNode }) {
  return <PublicShell layout="onboard">{children}</PublicShell>;
}
