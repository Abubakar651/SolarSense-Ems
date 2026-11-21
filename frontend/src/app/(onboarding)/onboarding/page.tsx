import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { OnboardingWizard } from '@/features/onboarding/components/onboarding-wizard';
import { getServices } from '@/services';
import { usingMocks } from '@/services/mode';

export const metadata: Metadata = { title: 'Set up your site' };

export default async function OnboardingPage() {
  // A site can only be set up once; afterwards it's edited in Settings. The demo always shows the wizard.
  if (!usingMocks() && (await getServices().account.getMe()).onboarded) redirect('/dashboard');
  return <OnboardingWizard />;
}
