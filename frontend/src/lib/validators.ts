export type Rule =
  | { kind: 'required' }
  | { kind: 'checked' }
  | { kind: 'email' }
  | { kind: 'min'; length: number }
  | { kind: 'match'; otherId: string }
  | { kind: 'num'; lo: number; hi: number };

export const rules = {
  required: (): Rule => ({ kind: 'required' }),
  checked: (): Rule => ({ kind: 'checked' }),
  email: (): Rule => ({ kind: 'email' }),
  min: (length: number): Rule => ({ kind: 'min', length }),
  match: (otherId: string): Rule => ({ kind: 'match', otherId }),
  num: (lo: number, hi: number): Rule => ({ kind: 'num', lo, hi }),
};

export interface ValidationContext {
  /** Visible label without the required star; used in "Enter your …" messages. */
  label: string;
  /** Raw value of another field (for `match`). */
  valueOf: (fieldId: string) => string;
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/**
 * Returns the first failing rule's message, or '' when the value is valid.
 * Text is trimmed before checking; checkboxes pass their checked state as a boolean.
 */
export function validateValue(
  input: string | boolean,
  fieldRules: Rule[],
  { label, valueOf }: ValidationContext,
): string {
  const value = typeof input === 'string' ? input.trim() : input;
  const name = label.toLowerCase();

  for (const rule of fieldRules) {
    if (rule.kind === 'required' && !value) return `Enter your ${name}.`;
    if (rule.kind === 'checked' && !value) return 'You need to accept to continue.';
    if (!value || typeof value !== 'string') continue;

    if (rule.kind === 'email' && !EMAIL_PATTERN.test(value)) {
      return 'Enter a valid email address, like name@example.com.';
    }
    if (rule.kind === 'min' && value.length < rule.length) {
      return `Use at least ${rule.length} characters (you have ${value.length}).`;
    }
    if (rule.kind === 'match' && value !== valueOf(rule.otherId)) {
      return "The two passwords don't match. Re-enter them.";
    }
    if (rule.kind === 'num') {
      const n = Number(value);
      if (!Number.isFinite(n) || n < rule.lo || n > rule.hi) {
        return `Enter a number between ${rule.lo} and ${rule.hi}.`;
      }
    }
  }
  return '';
}

/** 0 (empty) to 4: length, mixed case, a digit, and a symbol or a long password. */
export function passwordStrength(password: string): 0 | 1 | 2 | 3 | 4 {
  if (!password) return 0;
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/\d/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password) || password.length >= 14) score++;
  return score as 0 | 1 | 2 | 3 | 4;
}
