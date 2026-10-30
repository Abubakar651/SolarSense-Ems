import { test, expect } from '@playwright/test';
import { matrix } from './config';
import { compare, openScreen, saveFailure, shot, tolerance } from './harness';

/**
 * PARITY_SELF=1 compares the design with itself (proves the harness is deterministic);
 * otherwise the design is compared with the Next.js app on each ported route.
 */
const self = !!process.env.PARITY_SELF;
const { themes, widths, routes } = matrix();

for (const route of routes) {
  for (const theme of themes) {
    for (const width of widths) {
      test(`${route.id} · ${theme} · ${width}px`, async ({ browser }) => {
        const newContext = () =>
          browser.newContext({ reducedMotion: 'reduce', deviceScaleFactor: 1 });
        const ctxA = await newContext();
        const ctxB = await newContext();
        try {
          const pageA = await ctxA.newPage();
          const pageB = await ctxB.newPage();
          await openScreen(pageA, 'design', route, theme, width);
          await openScreen(pageB, self ? 'design' : 'port', route, theme, width);
          const a = await shot(pageA);
          const b = await shot(pageB);
          const diff = await compare(a, b);
          if (diff.mismatched > tolerance(diff.total)) {
            saveFailure(`${route.id}-${theme}-${width}`, a, b, diff);
          }
          expect(
            { size: diff.sizeB, mismatched: diff.mismatched },
            `design ${diff.sizeA.join('x')} vs ${self ? 'design' : 'port'} ${diff.sizeB.join('x')}`,
          ).toEqual({ size: diff.sizeA, mismatched: 0 });
        } finally {
          await ctxA.close();
          await ctxB.close();
        }
      });
    }
  }
}
