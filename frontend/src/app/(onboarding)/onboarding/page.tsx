import type { Metadata } from 'next';
import { OnboardingWizard } from '@/features/onboarding/components/onboarding-wizard';

export const metadata: Metadata = { title: 'Set up your site' };

export default function OnboardingPage() {
  return <OnboardingWizard />;
}
