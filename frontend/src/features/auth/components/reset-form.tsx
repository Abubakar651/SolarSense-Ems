'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules } from '@/lib/validators';
import { useToast } from '@/providers/toast-provider';
import { resetPasswordAction } from '../actions';
import { fieldValue } from '@/lib/form-values';

const NEW_PASSWORD_RULES = [rules.required(), rules.min(8)];
const CONFIRM_RULES = [rules.required(), rules.match('rs-password')];

/** `token` comes from the emailed link (/reset?token=…); the mock demo has none. */
export function ResetForm({ token }: { token?: string }) {
  const router = useRouter();
  const toast = useToast();
  const [pending, setPending] = useState(false);

  const submit = async (form: HTMLFormElement) => {
    if (pending) return;
    setPending(true);
    const result = await resetPasswordAction({ token, password: fieldValue(form, 'rs-password') });
    if (!result.ok) {
      setPending(false);
      toast(result.error);
      return;
    }
    toast('Password updated. Please log in.');
    router.push('/login');
  };

  return (
    <ValidatedForm onValid={(form) => void submit(form)}>
      <Field
        id="rs-password"
        label="New password"
        type="password"
        autoComplete="new-password"
        rules={NEW_PASSWORD_RULES}
      />
      <Field
        id="rs-confirm"
        label="Confirm new password"
        type="password"
        autoComplete="new-password"
        rules={CONFIRM_RULES}
      />
      <button className="btn btn-primary btn-block" type="submit" disabled={pending}>
        Update password
      </button>
    </ValidatedForm>
  );
}
