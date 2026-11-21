'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useToast } from '@/providers/toast-provider';
import { verifyEmailAction } from '../actions';

/** Redeems the emailed verification token, then sends the user to log in. */
export function ConfirmEmail({ token }: { token: string }) {
  const router = useRouter();
  const toast = useToast();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  const confirm = async () => {
    setPending(true);
    const result = await verifyEmailAction(token);
    if (!result.ok) {
      setPending(false);
      setError(result.error);
      return;
    }
    toast('Email confirmed. Log in to continue.');
    router.push('/login');
  };

  return (
    <>
      <button
        className="btn btn-primary btn-block"
        type="button"
        disabled={pending}
        onClick={() => void confirm()}
      >
        {pending ? 'Confirming…' : 'Confirm my email'}
      </button>
      {error && (
        <p className="hint" role="alert" style={{ marginTop: 'var(--sp-3)' }}>
          {error} <Link href="/login">Log in</Link> to get a new link.
        </p>
      )}
    </>
  );
}
