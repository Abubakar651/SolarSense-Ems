import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthLayout } from '@/components/layout/auth-layout';
import { Icon } from '@/components/ui/icon';
import { ResendEmail } from '@/features/auth/components/resend-email';

export const metadata: Metadata = { title: 'Verify email' };

export default function VerifyPage() {
  return (
    <AuthLayout route="verify" heading="One quick check before we start.">
      <div className="mail-ic">
        <Icon name="mail" size="lg" />
      </div>
      <h1>Check your email</h1>
      <p className="lead">
        We sent a verification link to <b>zaeem@example.com</b>. Open it to activate your account.
      </p>
      <Link className="btn btn-primary btn-block" href="/onboarding">
        I&apos;ve verified my email
      </Link>
      <ResendEmail />
    </AuthLayout>
  );
}
