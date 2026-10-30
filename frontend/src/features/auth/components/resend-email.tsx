'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useToast } from '@/providers/toast-provider';

const COOLDOWN_SECONDS = 30;

/** "Resend email" with a 30-second cooldown, plus the link back to sign-up. */
export function ResendEmail() {
  const toast = useToast();
  const [secondsLeft, setSecondsLeft] = useState(0);

  useEffect(() => {
    if (secondsLeft === 0) return;
    const timer = window.setTimeout(() => setSecondsLeft((seconds) => seconds - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [secondsLeft]);

  const resend = () => {
    if (secondsLeft) return;
    toast('Verification email sent');
    setSecondsLeft(COOLDOWN_SECONDS);
  };

  return (
    <>
      <div className="row between" style={{ marginTop: 'var(--sp-4)' }}>
        <button
          className="btn btn-ghost btn-sm"
          id="resendBtn"
          type="button"
          disabled={secondsLeft > 0}
          onClick={resend}
        >
          Resend email
        </button>
        <Link className="small" href="/signup">
          Use a different email
        </Link>
      </div>
      <p className="hint" id="resendHint" style={{ marginTop: 8 }} aria-live="polite">
        {secondsLeft > 0 ? `You can resend in ${secondsLeft}s.` : ''}
      </p>
    </>
  );
}
