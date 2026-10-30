'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { CheckField } from '@/components/forms/check';
import { Field } from '@/components/forms/field';
import { PasswordStrength } from '@/components/forms/password-strength';
import { ValidatedForm } from '@/components/forms/validated-form';
import { passwordStrength, rules } from '@/lib/validators';

const NAME_RULES = [rules.required()];
const EMAIL_RULES = [rules.required(), rules.email()];
const PASSWORD_RULES = [rules.required(), rules.min(8)];
const TERMS_RULES = [rules.checked()];

export function SignupForm() {
  const router = useRouter();
  const [strength, setStrength] = useState<0 | 1 | 2 | 3 | 4>(0);

  return (
    <ValidatedForm onValid={() => router.push('/verify')}>
      <Field
        id="su-name"
        label="Full name"
        type="text"
        autoComplete="name"
        placeholder="Zaeem"
        rules={NAME_RULES}
      />
      <Field
        id="su-email"
        label="Email address"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        rules={EMAIL_RULES}
      />
      <Field
        id="su-password"
        label="Password"
        type="password"
        autoComplete="new-password"
        rules={PASSWORD_RULES}
        hint="At least 8 characters. Password managers and paste are welcome."
        onValueChange={(value) => setStrength(passwordStrength(value))}
      />
      <PasswordStrength score={strength} />
      <CheckField id="su-terms" label="Terms" rules={TERMS_RULES}>
        I agree to the <Link href="/signup">Terms of Service</Link> and{' '}
        <Link href="/signup">Privacy Policy</Link>
      </CheckField>
      <button className="btn btn-primary btn-block" type="submit">
        Create account
      </button>
    </ValidatedForm>
  );
}
