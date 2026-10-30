import type { ReactNode } from 'react';
import { AuthBar } from './auth-bar';

export type PublicLayout = 'auth' | 'onboard' | 'landing';

/** Frame for pages outside the signed-in app: no sidebar or top bar, just the page. */
export function PublicShell({ layout, children }: { layout: PublicLayout; children: ReactNode }) {
  return (
    <>
      {layout !== 'landing' && <AuthBar layout={layout} />}
      <div id="app" data-layout={layout}>
        <div className="main-col">
          <main id="main" tabIndex={-1}>
            {children}
          </main>
        </div>
      </div>
    </>
  );
}
