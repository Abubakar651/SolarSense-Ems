'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Check } from '@/components/forms/check';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules, type Rule } from '@/lib/validators';
import { useToast } from '@/providers/toast-provider';
import { usingMocks } from '@/services/mode';
import { loginAction } from '../actions';
import { checkboxValue, fieldValue } from '@/lib/form-values';

// The mock demo lets an empty form log straight in; with the real API both fields are required.
const EMAIL_RULES: Rule[] = usingMocks() ? [rules.email()] : [rules.required(), rules.email()];
const PASSWORD_RULES: Rule[] = usingMocks() ? [] : [rules.required()];

export function LoginForm({ next }: { next?: string }) {
  const router = useRouter();
  const toast = useToast();
  const [pending, setPending] = useState(false);

  const submit = async (form: HTMLFormElement) => {
    if (pending) return;
    setPending(true);
    const result = await loginAction({
      email: fieldValue(form, 'login-email'),
      password: fieldValue(form, 'login-password'),
      remember: checkboxValue(form, 'remember'),
      next,
    });
    if (!result.ok) {
      setPending(false);
      toast(result.error);
      return;
    }
    toast('Logged in');
    router.push(result.data.redirectTo);
  };

  return (
    <ValidatedForm onValid={(form) => void submit(form)}>
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
      <button className="btn btn-primary btn-block" type="submit" disabled={pending}>
        {pending ? 'Logging in…' : 'Log in'}
      </button>
    </ValidatedForm>
  );
}
