import type { Metadata } from 'next';
import localFont from 'next/font/local';
import type { ReactNode } from 'react';
import { OffscreenLoops } from '@/components/layout/offscreen-loops';
import { AppProviders } from '@/providers/app-providers';
import '@/styles/globals.css';

// Pinned Latin subset of Inter (see ./fonts/README.md) so glyphs match the design exactly.
const inter = localFont({
  src: './fonts/inter-latin-variable.woff2',
  weight: '400 600',
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: { default: 'SolarSense · Smarter solar and battery', template: '%s · SolarSense' },
  description:
    'SolarSense plans your battery around peak tariffs and load-shedding, tells you when washing the panels pays off, and shows what you saved.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" data-theme="navy" className={inter.variable}>
      <body>
        <a className="skip" href="#main">
          Skip to main content
        </a>
        <AppProviders>{children}</AppProviders>
        <OffscreenLoops />
      </body>
    </html>
  );
}
