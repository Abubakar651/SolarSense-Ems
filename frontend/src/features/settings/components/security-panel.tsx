'use client';

import { Field } from '@/components/forms/field';
import { ValidatedForm } from '@/components/forms/validated-form';
import { rules } from '@/lib/validators';
import { useToast } from '@/providers/toast-provider';

const CURRENT_RULES = [rules.required()];
const NEW_RULES = [rules.required(), rules.min(8)];
const CONFIRM_RULES = [rules.required(), rules.match('pw-new')];

export function SecurityPanel() {
  const toast = useToast();

  return (
    <>
      <div className="card">
        <h2 style={{ marginBottom: 'var(--sp-4)' }}>Change password</h2>
        <ValidatedForm resetOnValid onValid={() => toast('Password changed')}>
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
          <button className="btn btn-primary" type="submit">
            Update password
          </button>
        </ValidatedForm>
      </div>
    </>
  );
}
