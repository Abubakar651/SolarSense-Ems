import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthLayout } from '@/components/layout/auth-layout';
import { ResetForm } from '@/features/auth/components/reset-form';
import { usingMocks } from '@/services/mode';

export const metadata: Metadata = { title: 'New password' };

interface ResetPageProps {
  searchParams: Promise<{ token?: string | string[] }>;
}

export default async function ResetPage({ searchParams }: ResetPageProps) {
  const { token } = await searchParams;
  const linkToken = typeof token === 'string' ? token : undefined;

  if (!usingMocks() && !linkToken) {
    return (
      <AuthLayout route="reset" heading="Choose a new password.">
        <h1>Reset link missing</h1>
        <p className="lead">Open the link from your reset email, or request a new one.</p>
        <Link className="btn btn-primary btn-block" href="/forgot">
          Request a new link
        </Link>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout route="reset" heading="Choose a new password.">
      <h1>Set a new password</h1>
      <p className="lead">Use at least 8 characters.</p>
      <ResetForm token={linkToken} />
    </AuthLayout>
  );
}
