import { expect, test, type Page } from '@playwright/test';

/** Same margin as the observer in src/lib/offscreen-loops.ts: loops resume just before they appear. */
const MARGIN = 80;

/**
 * Counts the infinite animations on the page and lists the ones breaking the rule: running while
 * their target is well outside the viewport, or paused while it is inside it.
 */
const survey = (page: Page) =>
  page.evaluate((margin) => {
    let running = 0;
    let paused = 0;
    const violations: string[] = [];
    for (const animation of document.getAnimations()) {
      const effect = animation.effect as KeyframeEffect | null;
      if (effect?.getTiming().iterations !== Infinity || !effect.target) continue;

      const { top, bottom, left, right } = effect.target.getBoundingClientRect();
      const within = (slack: number) =>
        bottom > -slack &&
        top < window.innerHeight + slack &&
        right > -slack &&
        left < window.innerWidth + slack;
      const label = `${animation.constructor.name} on <${effect.target.tagName.toLowerCase()} class="${effect.target.getAttribute('class')}">`;

      if (animation.playState === 'running') running++;
      if (animation.playState === 'paused') paused++;
      if (!within(margin) && animation.playState === 'running')
        violations.push(`${label} runs off screen`);
      if (within(0) && animation.playState === 'paused')
        violations.push(`${label} is paused on screen`);
    }
    return { running, paused, violations };
  }, MARGIN);

const scrollToBottom = (page: Page) =>
  page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));

for (const route of ['/', '/login', '/dashboard']) {
  test(`${route} runs looping animations only while they are on screen`, async ({ page }) => {
    await page.goto(route);
    await expect.poll(async () => (await survey(page)).violations).toEqual([]);

    await scrollToBottom(page);
    await expect.poll(async () => (await survey(page)).violations).toEqual([]);
  });
}

test('the landing page pauses the loops below the fold and plays them once scrolled to', async ({
  page,
}) => {
  await page.goto('/');
  await expect.poll(async () => (await survey(page)).paused).toBeGreaterThan(0);

  await scrollToBottom(page);
  await expect.poll(async () => (await survey(page)).running).toBeGreaterThan(0);
});
