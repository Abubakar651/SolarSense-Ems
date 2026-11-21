'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules } from '@/lib/validators';
import { useToast } from '@/providers/toast-provider';
import { forgotPasswordAction } from '../actions';
import { fieldValue } from '@/lib/form-values';

const EMAIL_RULES = [rules.required(), rules.email()];

export function ForgotForm() {
  const router = useRouter();
  const toast = useToast();
  const [pending, setPending] = useState(false);

  const submit = async (form: HTMLFormElement) => {
    if (pending) return;
    setPending(true);
    const result = await forgotPasswordAction(fieldValue(form, 'fg-email'));
    if (!result.ok) {
      setPending(false);
      toast(result.error);
      return;
    }
    router.push('/forgot/sent');
  };

  return (
    <ValidatedForm onValid={(form) => void submit(form)}>
      <Field
        id="fg-email"
        label="Email address"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        rules={EMAIL_RULES}
      />
      <button className="btn btn-primary btn-block" type="submit" disabled={pending}>
        Send reset link
      </button>
    </ValidatedForm>
  );
}
