'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Check } from '@/components/forms/check';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules } from '@/lib/validators';
import { useToast } from '@/providers/toast-provider';

const EMAIL_RULES = [rules.required(), rules.email()];
const PASSWORD_RULES = [rules.required()];

export function LoginForm() {
  const router = useRouter();
  const toast = useToast();

  return (
    <ValidatedForm
      onValid={() => {
        toast('Logged in');
        router.push('/dashboard');
      }}
    >
      <Field
        id="login-email"
        label="Email address"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        rules={EMAIL_RULES}
      />
      <Field
        id="login-password"
        label="Password"
        type="password"
        autoComplete="current-password"
        rules={PASSWORD_RULES}
      />
      <div className="row between" style={{ margin: '-4px 0 var(--sp-5)' }}>
        <Check name="remember" label="Keep me logged in" />
        <Link href="/forgot" className="small">
          Forgot password?
        </Link>
      </div>
      <button className="btn btn-primary btn-block" type="submit">
        Log in
      </button>
    </ValidatedForm>
  );
}
