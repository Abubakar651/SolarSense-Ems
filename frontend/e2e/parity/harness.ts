import fs from 'node:fs';
import path from 'node:path';
import type { Page } from '@playwright/test';
import { pinDesignFonts } from './fonts';
import { applyIntentionalCopyChanges } from './intentional-diffs';
import {
  DESIGN_THEME_KEY,
  DESIGN_URL,
  REPORT_DIR,
  VIEWPORT_HEIGHT,
  type RouteSpec,
  type Theme,
} from './config';

export type Source = 'design' | 'port';

/**
 * Same in both pages: hide the design-only "Preview:" jump select and the caret, and
 * collapse motion to its end state (the design's reduced-motion rule keeps stagger delays,
 * so staggered or looping entrances would otherwise be caught mid-flight).
 */
const FREEZE_CSS =
  '.jump{display:none!important}*{caret-color:transparent!important}' +
  '*,*::before,*::after{animation-delay:0s!important;animation-duration:0s!important;' +
  'transition-delay:0s!important;transition-duration:0s!important}';

export async function openScreen(
  page: Page,
  source: Source,
  route: RouteSpec,
  theme: Theme,
  width: number,
): Promise<void> {
  await page.setViewportSize({ width, height: VIEWPORT_HEIGHT });
  const themeValue = source === 'design' ? DESIGN_THEME_KEY[theme] : theme;
  await page.addInitScript((value) => {
    try {
      localStorage.setItem('ss-theme', value);
    } catch {
      // storage unavailable: the page falls back to its default theme
    }
  }, themeValue);
  if (source === 'design') await pinDesignFonts(page);
  await page.goto(source === 'design' ? `${DESIGN_URL}#/${route.designHash}` : route.portPath);
  await page.addStyleTag({ content: FREEZE_CSS });
  if (source === 'design') await applyIntentionalCopyChanges(page);
  await page.evaluate(() => document.fonts.ready);
  // The design keeps stagger delays under reduced motion; let every entrance finish.
  await page.waitForTimeout(1800);
  // A theme switched after first paint can leave stale anti-aliased edge pixels from incremental
  // repainting; force one full repaint on both pages so only the final state is compared.
  await page.evaluate(() => {
    document.body.style.visibility = 'hidden';
    void document.body.offsetHeight;
    document.body.style.visibility = '';
  });
  await page.waitForTimeout(100);
}

export async function shot(page: Page): Promise<Buffer> {
  return page.screenshot({ fullPage: true, animations: 'disabled', caret: 'hide' });
}

export interface Diff {
  mismatched: number;
  total: number;
  sizeA: [number, number];
  sizeB: [number, number];
  diffPng?: Buffer;
}

export async function compare(a: Buffer, b: Buffer): Promise<Diff> {
  const { default: pixelmatch } = await import('pixelmatch');
  const png = await import('pngjs');
  const PNG = png.PNG ?? png.default.PNG;
  const imgA = PNG.sync.read(a);
  const imgB = PNG.sync.read(b);
  const sizeA: [number, number] = [imgA.width, imgA.height];
  const sizeB: [number, number] = [imgB.width, imgB.height];
  if (imgA.width !== imgB.width || imgA.height !== imgB.height) {
    return { mismatched: Number.POSITIVE_INFINITY, total: imgA.width * imgA.height, sizeA, sizeB };
  }
  const out = new PNG({ width: imgA.width, height: imgA.height });
  const mismatched = pixelmatch(imgA.data, imgB.data, out.data, imgA.width, imgA.height, {
    threshold: 0,
  });
  return {
    mismatched,
    total: imgA.width * imgA.height,
    sizeA,
    sizeB,
    diffPng: PNG.sync.write(out),
  };
}

export function saveFailure(name: string, a: Buffer, b: Buffer, diff: Diff): void {
  fs.mkdirSync(REPORT_DIR, { recursive: true });
  fs.writeFileSync(path.join(REPORT_DIR, `${name}.a.png`), a);
  fs.writeFileSync(path.join(REPORT_DIR, `${name}.b.png`), b);
  if (diff.diffPng) fs.writeFileSync(path.join(REPORT_DIR, `${name}.diff.png`), diff.diffPng);
}

/** Allowed mismatching pixels as a fraction of the image (default: none). */
export function tolerance(total: number): number {
  return Math.floor(total * Number(process.env.PARITY_TOLERANCE ?? 0));
}
