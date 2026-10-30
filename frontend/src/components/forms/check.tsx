'use client';

import { useEffect, type ReactNode } from 'react';
import type { Rule } from '@/lib/validators';
import { FieldError } from './field-error';
import { useFormField } from './validated-form';

/** Plain checkbox with its label (no validation). */
export function Check({ name, label }: { name: string; label: string }) {
  return (
    <label className="check">
      <input type="checkbox" name={name} />
      {` ${label}`}
    </label>
  );
}

interface CheckFieldProps {
  id: string;
  label: string;
  rules: Rule[];
  children: ReactNode;
}

/** Checkbox that must be accepted; shows its error under the label. */
export function CheckField({ id, label, rules, children }: CheckFieldProps) {
  const { errors, register, check } = useFormField();
  const error = errors[id] ?? '';

  useEffect(() => register(id, { label, rules }), [id, label, rules, register]);

  return (
    <div className="field">
      <label className="check">
        <input
          type="checkbox"
          id={id}
          name={id}
          aria-describedby={`${id}-err`}
          aria-invalid={error ? true : undefined}
          onBlur={() => check(id)}
        />{' '}
        <span>{children}</span>
      </label>
      <FieldError id={`${id}-err`} message={error} />
    </div>
  );
}
