import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthLayout } from '@/components/layout/auth-layout';
import { Icon } from '@/components/ui/icon';
import { ConfirmEmail } from '@/features/auth/components/confirm-email';
import { ResendEmail } from '@/features/auth/components/resend-email';
import { readPendingEmail } from '@/services/http/session';
import { usingMocks } from '@/services/mode';

export const metadata: Metadata = { title: 'Verify email' };

const SAMPLE_EMAIL = 'zaeem@example.com';

interface VerifyPageProps {
  searchParams: Promise<{ token?: string | string[] }>;
}

export default async function VerifyPage({ searchParams }: VerifyPageProps) {
  const mocks = usingMocks();
  const { token } = await searchParams;

  // Opened from the emailed link: confirm with a button press rather than on page load, so mail
  // scanners that prefetch links can't use up the one-time token.
  if (!mocks && typeof token === 'string') {
    return (
      <AuthLayout route="verify" heading="One quick check before we start.">
        <div className="mail-ic">
          <Icon name="mail" size="lg" />
        </div>
        <h1>Confirm your email</h1>
        <p className="lead">Press the button to activate your account.</p>
        <ConfirmEmail token={token} />
      </AuthLayout>
    );
  }

  const email = mocks ? SAMPLE_EMAIL : await readPendingEmail();

  return (
    <AuthLayout route="verify" heading="One quick check before we start.">
      <div className="mail-ic">
        <Icon name="mail" size="lg" />
      </div>
      <h1>Check your email</h1>
      <p className="lead">
        We sent a verification link to {email ? <b>{email}</b> : 'your email address'}. Open it to
        activate your account.
      </p>
      <Link className="btn btn-primary btn-block" href={mocks ? '/onboarding' : '/login'}>
        I&apos;ve verified my email
      </Link>
      <ResendEmail />
    </AuthLayout>
  );
}
