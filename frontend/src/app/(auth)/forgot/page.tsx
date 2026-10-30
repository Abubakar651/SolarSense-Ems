import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthLayout } from '@/components/layout/auth-layout';
import { ForgotForm } from '@/features/auth/components/forgot-form';

export const metadata: Metadata = { title: 'Reset password' };

export default function ForgotPage() {
  return (
    <AuthLayout route="forgot" heading="Locked out? It happens. We'll get you back in.">
      <h1>Reset your password</h1>
      <p className="lead">Enter the email you signed up with and we&apos;ll send a reset link.</p>
      <ForgotForm />
      <p className="auth-foot">
        <Link href="/login">Back to log in</Link>
      </p>
    </AuthLayout>
  );
}
