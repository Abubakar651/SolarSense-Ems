'use client';

import { useRouter } from 'next/navigation';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules } from '@/lib/validators';

const EMAIL_RULES = [rules.required(), rules.email()];

export function ForgotForm() {
  const router = useRouter();

  return (
    <ValidatedForm onValid={() => router.push('/forgot/sent')}>
      <Field
        id="fg-email"
        label="Email address"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        rules={EMAIL_RULES}
      />
      <button className="btn btn-primary btn-block" type="submit">
        Send reset link
      </button>
    </ValidatedForm>
  );
}
