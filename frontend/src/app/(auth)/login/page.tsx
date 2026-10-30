import type { Metadata } from 'next';
import Link from 'next/link';
import { AuthLayout } from '@/components/layout/auth-layout';
import { LoginForm } from '@/features/auth/components/login-form';

export const metadata: Metadata = { title: 'Log in' };

export default function LoginPage() {
  return (
    <AuthLayout
      route="login"
      heading="Know what your solar and battery are doing, and what to do next."
      bullets={[
        'Lower bills by avoiding expensive peak-hour grid power',
        'Battery planned ahead of load-shedding',
        'Know exactly when washing the panels pays off',
      ]}
      stat={{ value: 'PKR 14,820', label: 'sample monthly saving shown in this design' }}
    >
      <h1>Welcome back</h1>
      <p className="lead">Log in to see how your system is performing.</p>
      <LoginForm />
      <p className="auth-foot">
        New to SolarSense? <Link href="/signup">Create an account</Link>
      </p>
    </AuthLayout>
  );
}
