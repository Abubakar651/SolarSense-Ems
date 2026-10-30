// Dev helper: prints bounding rects of CSS selectors in the design and the port at a given width.
// usage: node scripts/rect-check.mjs <route> <width> <selector> [<selector> ...]
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from '@playwright/test';

const [route, width, ...selectors] = process.argv.slice(2);
const design =
  pathToFileURL(path.resolve(import.meta.dirname, '../design/index.html')).href + `#/${route}`;
const port = `http://localhost:3100/${route === 'landing' ? '' : route}`;

const browser = await chromium.launch();
for (const [label, url] of [
  ['design', design],
  ['port', port],
]) {
  const page = await browser.newPage({ viewport: { width: Number(width), height: 900 } });
  if (process.env.THEME)
    await page.addInitScript((t) => localStorage.setItem('ss-theme', t), process.env.THEME);
  await page.goto(url);
  await page.addStyleTag({
    content: '*,*::before,*::after{animation:none!important;transition:none!important}',
  });
  await page.waitForTimeout(800);
  for (const selector of selectors) {
    const rects = await page.$$eval(selector, (els) =>
      els.slice(0, 4).map((el) => {
        const r = el.getBoundingClientRect();
        return `${r.x.toFixed(3)},${r.y.toFixed(3)} ${r.width.toFixed(3)}x${r.height.toFixed(3)}`;
      }),
    );
    console.log(label.padEnd(7), selector.padEnd(24), rects.join(' | '));
  }
  await page.close();
}
await browser.close();
