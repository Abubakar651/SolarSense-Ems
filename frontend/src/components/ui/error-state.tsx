import type { ReactNode } from 'react';

interface ErrorStateProps {
  title: string;
  message: string;
  /** The button or link that gets the user out (retry, go home). */
  action: ReactNode;
  /** Support reference shown under the message (e.g. an error digest). */
  reference?: string;
}

/** Full-width message for pages that cannot be shown: not found, or something broke. */
export function ErrorState({ title, message, action, reference }: ErrorStateProps) {
  return (
    <section
      className="empty"
      role="alert"
      style={{ display: 'grid', gap: 12, placeItems: 'center' }}
    >
      <h1 tabIndex={-1}>{title}</h1>
      <p>{message}</p>
      {reference && <p className="xs faint">{`Reference: ${reference}`}</p>}
      {action}
    </section>
  );
}
