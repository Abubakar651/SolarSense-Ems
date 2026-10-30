'use client';

import { useRouter } from 'next/navigation';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules } from '@/lib/validators';
import { useToast } from '@/providers/toast-provider';

const NEW_PASSWORD_RULES = [rules.required(), rules.min(8)];
const CONFIRM_RULES = [rules.required(), rules.match('rs-password')];

export function ResetForm() {
  const router = useRouter();
  const toast = useToast();

  return (
    <ValidatedForm
      onValid={() => {
        toast('Password updated. Please log in.');
        router.push('/login');
      }}
    >
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
      <button className="btn btn-primary btn-block" type="submit">
        Update password
      </button>
    </ValidatedForm>
  );
}
