import { expect, test } from '@playwright/test';
import { ALL_ROUTES } from './routes';

const WIDTHS = [320, 375, 768, 1024, 1440, 1920] as const;
const TOUCH_TARGET_MIN = 32;

test.use({ reducedMotion: 'reduce' });

for (const width of WIDTHS) {
  test.describe(`${width}px`, () => {
    test.use({ viewport: { width, height: 900 } });

    for (const route of ALL_ROUTES) {
      test(`${route} fits the viewport and has usable tap targets`, async ({ page }) => {
        await page.goto(route);
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(300);

        const report = await page.evaluate((minTarget) => {
          const limit = document.documentElement.clientWidth;
          const visible = (el: Element) => el.getClientRects().length > 0;
          const describe = (el: Element) =>
            `${el.tagName.toLowerCase()}.${String(el.className).trim().split(/\s+/).slice(0, 2).join('.')}`;

          // Anything inside its own scroller (tables, tab strips) may extend past the page.
          const inScroller = (el: Element) =>
            !!el.closest('.tbl-wrap, .tabs, .land-drawer, dialog');
          const overflowing = [...document.querySelectorAll('body *')]
            .filter((el) => visible(el) && !el.closest('svg') && !inScroller(el))
            .filter((el) => el.getBoundingClientRect().right > limit + 0.5)
            .slice(0, 5)
            .map(describe);

          const smallTargets = [
            ...document.querySelectorAll(
              'button, a[href], select, input:not([type=checkbox]):not([type=radio]):not([type=range])',
            ),
          ]
            .filter((el) => visible(el) && getComputedStyle(el).display !== 'inline')
            .filter((el) => !el.closest('.switch, .sr-only') && !el.classList.contains('sr-only'))
            .filter((el) => el.getBoundingClientRect().height < minTarget)
            .slice(0, 5)
            .map(describe);

          return {
            scrollWidth: document.documentElement.scrollWidth,
            limit,
            overflowing,
            smallTargets,
          };
        }, TOUCH_TARGET_MIN);

        expect(
          report.scrollWidth,
          `page is wider than the viewport: ${report.overflowing.join(', ')}`,
        ).toBeLessThanOrEqual(report.limit);
        expect(report.smallTargets, 'interactive elements under 32px tall').toEqual([]);
      });
    }
  });
}
