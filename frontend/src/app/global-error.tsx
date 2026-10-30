'use client';

import '@/styles/globals.css';

/** Replaces the root layout when it fails, so it must render its own <html> and <body>. */
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en" data-theme="navy">
      <body>
        <section
          className="empty"
          role="alert"
          style={{ minHeight: '100dvh', display: 'grid', placeContent: 'center', gap: 12 }}
        >
          <h1>Something went wrong</h1>
          <p>SolarSense hit an unexpected problem. Please try again.</p>
          <button className="btn btn-primary" type="button" onClick={reset}>
            Try again
          </button>
        </section>
      </body>
    </html>
  );
}
