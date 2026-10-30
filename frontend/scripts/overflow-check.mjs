// Dev helper: lists elements that extend past the viewport, on the app (needs `pnpm start -p 3100`)
// and on the design. usage: node scripts/overflow-check.mjs <route> <width>   (e.g. billing 320)
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from '@playwright/test';

const [route, width] = process.argv.slice(2);
const design =
  pathToFileURL(path.resolve(import.meta.dirname, '../design/index.html')).href + `#/${route}`;
const port = `http://localhost:3100/${route === 'landing' ? '' : route}`;

const browser = await chromium.launch();
for (const [label, url] of [
  ['design', design],
  ['port', port],
]) {
  const page = await browser.newPage({ viewport: { width: Number(width), height: 900 } });
  await page.goto(url);
  await page.waitForTimeout(1200);
  const report = await page.evaluate(() => {
    const limit = document.documentElement.clientWidth;
    const offenders = [...document.querySelectorAll('body *')]
      .filter((el) => el.getClientRects().length && el.getBoundingClientRect().right > limit + 0.5)
      .slice(0, 6)
      .map(
        (el) =>
          `${el.tagName.toLowerCase()}.${String(el.className).slice(0, 30)} right=${el.getBoundingClientRect().right.toFixed(1)}`,
      );
    return { scrollWidth: document.documentElement.scrollWidth, limit, offenders };
  });
  console.log(label.padEnd(7), JSON.stringify(report));
  await page.close();
}
await browser.close();
