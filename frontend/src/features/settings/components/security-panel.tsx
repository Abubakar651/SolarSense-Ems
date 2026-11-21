'use client';

import { useState } from 'react';
import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules } from '@/lib/validators';
import { useToast } from '@/providers/toast-provider';
import type { ActionResult } from '@/services/http/action-result';
import { fieldValue } from '@/lib/form-values';

const CURRENT_RULES = [rules.required()];
const NEW_RULES = [rules.required(), rules.min(8)];
const CONFIRM_RULES = [rules.required(), rules.match('pw-new')];

interface SecurityPanelProps {
  changePassword: (input: { current: string; next: string }) => Promise<ActionResult>;
}

export function SecurityPanel({ changePassword }: SecurityPanelProps) {
  const toast = useToast();
  const [pending, setPending] = useState(false);

  const submit = async (form: HTMLFormElement) => {
    if (pending) return;
    setPending(true);
    const result = await changePassword({
      current: fieldValue(form, 'pw-cur'),
      next: fieldValue(form, 'pw-new'),
    });
    setPending(false);
    if (!result.ok) {
      toast(result.error);
      return;
    }
    form.reset();
    toast('Password changed. Other devices have been logged out.');
  };

  return (
    <>
      <div className="card">
        <h2 style={{ marginBottom: 'var(--sp-4)' }}>Change password</h2>
        <ValidatedForm onValid={(form) => void submit(form)}>
          <Field
            id="pw-cur"
            label="Current password"
            type="password"
            autoComplete="current-password"
            rules={CURRENT_RULES}
          />
          <Field
            id="pw-new"
            label="New password"
            type="password"
            autoComplete="new-password"
            rules={NEW_RULES}
          />
          <Field
            id="pw-conf"
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            rules={CONFIRM_RULES}
          />
          <button className="btn btn-primary" type="submit" disabled={pending}>
            Update password
          </button>
        </ValidatedForm>
      </div>
    </>
  );
}
