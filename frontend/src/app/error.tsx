'use client';

import { PublicShell } from '@/components/layout/public-shell';
import { ErrorState } from '@/components/ui/error-state';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/** Last-resort boundary for public pages (the signed-in app has its own, inside its shell). */
export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <PublicShell layout="landing">
      <ErrorState
        title="Something went wrong"
        message="We could not load this page. Please try again."
        reference={error.digest}
        action={
          <button className="btn btn-primary" type="button" onClick={reset}>
            Try again
          </button>
        }
      />
    </PublicShell>
  );
}
