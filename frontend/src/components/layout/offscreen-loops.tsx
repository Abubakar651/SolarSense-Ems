'use client';

import { usePathname } from 'next/navigation';
import { useEffect } from 'react';
import { pauseOffscreenLoops } from '@/lib/offscreen-loops';

/** Mounted once in the root layout; scans again on navigation because the layout outlives each page. */
export function OffscreenLoops() {
  const pathname = usePathname();
  useEffect(() => pauseOffscreenLoops(), [pathname]);
  return null;
}
