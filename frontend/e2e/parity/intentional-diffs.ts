import type { Page } from '@playwright/test';

/**
 * Copy the port deliberately words differently from the design preview (the preview's
 * "(preview)" hints do not belong in the product). Applied to the design page only, so the
 * diff isolates real regressions. Keep this list short and justified.
 */
const COPY_CHANGES: Array<{ selector: string; from: string; to: string }> = [
  { selector: 'a[href="#/reset"].btn', from: 'Open reset link (preview)', to: 'Open reset link' },
];

export async function applyIntentionalCopyChanges(page: Page): Promise<void> {
  await page.evaluate((changes) => {
    for (const { selector, from, to } of changes) {
      document.querySelectorAll(selector).forEach((el) => {
        if (el.textContent === from) el.textContent = to;
      });
    }
  }, COPY_CHANGES);
}
