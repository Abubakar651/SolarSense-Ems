'use client';

import { useEffect, useState, type HTMLInputTypeAttribute } from 'react';
import { Icon } from '@/components/ui/icon';
import type { Rule } from '@/lib/validators';
import { FieldError } from './field-error';
import { useFormField } from './validated-form';

interface FieldProps {
  id: string;
  label: string;
  type: HTMLInputTypeAttribute;
  autoComplete: string;
  placeholder?: string;
  rules: Rule[];
  hint?: string;
  /** Multi-step forms: the step this field belongs to (see ValidatedForm `activeGroup`). */
  group?: string;
  inputMode?: 'decimal' | 'numeric';
  /** Fires on every change; used for live feedback such as the password strength meter. */
  onValueChange?: (value: string) => void;
}

/** Labelled text/email/password input wired into the surrounding <ValidatedForm>. */
export function Field({
  id,
  label,
  type,
  autoComplete,
  placeholder = '',
  rules,
  hint,
  group,
  inputMode,
  onValueChange,
}: FieldProps) {
  const { errors, register, check } = useFormField();
  const [revealed, setRevealed] = useState(false);
  const required = rules.some((rule) => rule.kind === 'required');
  const error = errors[id] ?? '';
  const isPassword = type === 'password';

  useEffect(() => register(id, { label, rules, group }), [id, label, rules, group, register]);

  const input = (
    <input
      className="input"
      id={id}
      name={id}
      type={isPassword && revealed ? 'text' : type}
      inputMode={inputMode}
      autoComplete={autoComplete}
      placeholder={placeholder}
      aria-describedby={[hint ? `${id}-hint` : '', `${id}-err`].filter(Boolean).join(' ')}
      aria-required={required || undefined}
      aria-invalid={error ? true : undefined}
      onBlur={(event) => event.target.value !== '' && check(id)}
      onChange={(event) => onValueChange?.(event.target.value)}
    />
  );

  return (
    <div className="field">
      <label htmlFor={id}>
        {/* One text node: the design's label is a single string, and splitting it shifts the star by 1/64px. */}
        {required ? `${label} ` : label}
        {required && (
          <span className="req" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {isPassword ? (
        <div className="pw">
          {input}
          <button
            type="button"
            aria-label={revealed ? 'Hide password' : 'Show password'}
            aria-pressed={revealed}
            onClick={() => setRevealed((value) => !value)}
          >
            <Icon name={revealed ? 'eyeoff' : 'eye'} />
          </button>
        </div>
      ) : (
        input
      )}
      {hint && (
        <p className="hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      <FieldError id={`${id}-err`} message={error} />
    </div>
  );
}
