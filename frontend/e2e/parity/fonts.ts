import fs from 'node:fs';
import path from 'node:path';
import type { Page } from '@playwright/test';

const FONT_FILE = path.resolve(__dirname, '../../src/app/fonts/inter-latin-variable.woff2');

/** The Latin faces the design requests from Google Fonts (weights 400, 500, 600). */
const FONT_CSS = [400, 500, 600]
  .map(
    (
      weight,
    ) => `@font-face{font-family:'Inter';font-style:normal;font-weight:${weight};font-display:swap;
src:url(https://fonts.gstatic.com/s/inter/v20/pinned.woff2) format('woff2');
unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}`,
  )
  .join('\n');

/**
 * Serves the design's Google Fonts requests from the pinned local file, so both pages render the
 * same glyphs regardless of network access or a later Google font update.
 */
export async function pinDesignFonts(page: Page): Promise<void> {
  await page.route('https://fonts.googleapis.com/**', (route) =>
    route.fulfill({ contentType: 'text/css', body: FONT_CSS }),
  );
  await page.route('https://fonts.gstatic.com/**', (route) =>
    route.fulfill({ contentType: 'font/woff2', body: fs.readFileSync(FONT_FILE) }),
  );
}
