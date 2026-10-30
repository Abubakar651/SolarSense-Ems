'use client';

import { ErrorState } from '@/components/ui/error-state';

interface AppErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

/** A screen failed to load: keeps the sidebar and top bar, shows a retry in the page area. */
export default function AppError({ error, reset }: AppErrorProps) {
  return (
    <ErrorState
      title="We couldn't load this screen"
      message="Your data is safe. Please try again in a moment."
      reference={error.digest}
      action={
        <button className="btn btn-primary" type="button" onClick={reset}>
          Try again
        </button>
      }
    />
  );
}
