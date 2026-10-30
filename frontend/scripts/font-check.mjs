// Dev helper: lists the font files each page actually downloads (URL, size, sha1) to compare design vs port.
import crypto from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from '@playwright/test';

const design =
  pathToFileURL(path.resolve(import.meta.dirname, '../design/index.html')).href + '#/login';
const port = 'http://localhost:3100/login';

const browser = await chromium.launch();
for (const [label, url] of [
  ['design', design],
  ['port', port],
]) {
  const page = await browser.newPage();
  const fonts = [];
  page.on('response', async (res) => {
    const type = res.headers()['content-type'] ?? '';
    if (/font|woff/.test(type) || /\.woff2?($|\?)/.test(res.url())) {
      const body = await res.body();
      fonts.push({
        url: res.url().slice(0, 110),
        bytes: body.length,
        sha1: crypto.createHash('sha1').update(body).digest('hex').slice(0, 10),
      });
    }
  });
  await page.goto(url);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(1000);
  const faces = await page.evaluate(() =>
    [...document.fonts].map(
      (f) => `${f.family} ${f.weight} ${f.style} ${f.status} ${f.unicodeRange.slice(0, 30)}`,
    ),
  );
  console.log(label, JSON.stringify({ fonts, faces }, null, 1));
  await page.close();
}
await browser.close();
