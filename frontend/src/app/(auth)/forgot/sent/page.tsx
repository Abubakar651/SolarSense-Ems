import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthLayout } from '@/components/layout/auth-layout';
import { Icon } from '@/components/ui/icon';

export const metadata: Metadata = { title: 'Reset link sent' };

export default function ForgotSentPage() {
  return (
    <AuthLayout route="forgot-sent" heading="Reset link on its way.">
      <div className="mail-ic">
        <Icon name="mail" size="lg" />
      </div>
      <h1>Reset link sent</h1>
      <p className="lead">
        If an account exists for that email, you&apos;ll receive a link within a few minutes. It
        expires in 30 minutes.
      </p>
      <Link className="btn btn-primary btn-block" href="/reset">
        Open reset link
      </Link>
      <p className="auth-foot">
        <Link href="/login">Back to log in</Link>
      </p>
    </AuthLayout>
  );
}
