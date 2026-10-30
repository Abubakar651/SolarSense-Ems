import type { Metadata } from 'next';
import { AuthLayout } from '@/components/layout/auth-layout';
import { ResetForm } from '@/features/auth/components/reset-form';

export const metadata: Metadata = { title: 'New password' };

export default function ResetPage() {
  return (
    <AuthLayout route="reset" heading="Choose a new password.">
      <h1>Set a new password</h1>
      <p className="lead">Use at least 8 characters.</p>
      <ResetForm />
    </AuthLayout>
  );
}
