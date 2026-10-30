import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthLayout } from '@/components/layout/auth-layout';
import { SignupForm } from '@/features/auth/components/signup-form';

export const metadata: Metadata = { title: 'Create account' };

export default function SignupPage() {
  return (
    <AuthLayout
      route="signup"
      heading="Set up in minutes. See savings the same day."
      bullets={[
        'Create your account',
        'Tell us about your panels and battery',
        'Connect your inverter and get your first plan',
      ]}
    >
      <h1>Create your account</h1>
      <p className="lead">For homes and buildings with solar and a battery.</p>
      <SignupForm />
      <p className="auth-foot">
        Already have an account? <Link href="/login">Log in</Link>
      </p>
    </AuthLayout>
  );
}
