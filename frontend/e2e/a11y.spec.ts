import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { ALL_ROUTES } from './routes';

// Entrance animations are off, so contrast is measured on settled colours.
test.use({ reducedMotion: 'reduce' });

// Serious and critical axe violations fail the run; minor and moderate ones are reported only.
const BLOCKING = new Set(['serious', 'critical']);

for (const route of ALL_ROUTES) {
  test(`${route} has no serious accessibility violations`, async ({ page }) => {
    await page.goto(route);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);

    const { violations } = await new AxeBuilder({ page }).analyze();
    const blocking = violations
      .filter((v) => v.impact && BLOCKING.has(v.impact))
      .map(
        (v) =>
          `${v.id} (${v.impact}): ${v.nodes
            .slice(0, 3)
            .map((n) => n.target.join(' '))
            .join(' | ')}`,
      );
    expect(blocking).toEqual([]);
  });
}
