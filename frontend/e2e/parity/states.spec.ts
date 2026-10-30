import { expect, test, type Page } from '@playwright/test';
import { ROUTES } from './config';
import { compare, openScreen, saveFailure, shot, tolerance } from './harness';

/**
 * Interaction states: the same scripted actions run on the design and on the app, then the
 * screenshots are compared. Selectors are ids and classes the two share.
 */
interface Scenario {
  name: string;
  route: string;
  width: number;
  act: (page: Page) => Promise<void>;
}

const hoverChart =
  (selector: string, share = 0.4) =>
  async (page: Page) => {
    const box = await page.locator(selector).boundingBox();
    if (!box) throw new Error(`no box for ${selector}`);
    await page.mouse.move(box.x + box.width * share, box.y + 90);
  };

const fillOnboardingStep = [
  async (page: Page) => {
    await page.fill('#ob-site', 'My Site');
    await page.fill('#ob-addr', 'Street 1, Area');
    await page.fill('#ob-city', 'Some City');
  },
  async (page: Page) => {
    await page.fill('#ob-pv', '8.0');
    await page.fill('#ob-bat', '10.0');
    await page.fill('#ob-sn', 'SN-12345');
  },
  async (page: Page) => {
    await page.fill('#ob-peak', '48.00');
    await page.fill('#ob-off', '35.00');
    await page.fill('#ob-exp', '27.00');
  },
];

async function throughOnboarding(page: Page, steps: number) {
  for (let step = 0; step < steps; step++) {
    await fillOnboardingStep[step]?.(page);
    await page.click('#onbNext');
    await page.waitForTimeout(150);
  }
}

const scenarios: Scenario[] = [
  { name: 'app drawer open', route: 'dashboard', width: 375, act: (p) => p.click('#menuBtn') },
  { name: 'user menu open', route: 'dashboard', width: 1280, act: (p) => p.click('#userBtn') },
  { name: 'chart tooltip', route: 'dashboard', width: 1280, act: hoverChart('#chart-dash') },
  { name: 'chart tooltip', route: 'dashboard', width: 375, act: hoverChart('#chart-dash', 0.5) },
  { name: 'menu drawer open', route: 'landing', width: 375, act: (p) => p.click('#landMenuBtn') },
  { name: 'faq open', route: 'landing', width: 1280, act: (p) => p.click('.faq summary >> nth=0') },
  {
    name: 'hover primary button',
    route: 'landing',
    width: 1280,
    act: (p) => p.hover('.hero .btn-primary'),
  },
  { name: 'empty submit', route: 'login', width: 1280, act: (p) => p.click('button[type=submit]') },
  {
    name: 'keyboard focus',
    route: 'login',
    width: 375,
    // The design focuses the page heading on load (so Tab would start from there); start from a field instead.
    act: async (p) => {
      await p.focus('#login-password');
      await p.keyboard.press('Tab');
    },
  },
  {
    name: 'bad email and strong password',
    route: 'signup',
    width: 1280,
    act: async (p) => {
      await p.fill('#su-email', 'not-an-email');
      await p.fill('#su-password', 'Abcdef1!');
      await p.keyboard.press('Tab');
    },
  },
  { name: 'step 1 errors', route: 'onboarding', width: 375, act: (p) => p.click('#onbNext') },
  { name: 'step 2 system', route: 'onboarding', width: 1280, act: (p) => throughOnboarding(p, 1) },
  { name: 'step 3 tariff', route: 'onboarding', width: 1280, act: (p) => throughOnboarding(p, 2) },
  { name: 'step 4 review', route: 'onboarding', width: 1280, act: (p) => throughOnboarding(p, 3) },
  { name: 'step 4 review', route: 'onboarding', width: 375, act: (p) => throughOnboarding(p, 3) },
  {
    name: '7 days',
    route: 'savings',
    width: 1280,
    act: (p) => p.click('#savRange button >> nth=0'),
  },
  {
    name: '12 months',
    route: 'savings',
    width: 375,
    act: (p) => p.click('#savRange button >> nth=2'),
  },
  { name: 'wait advice', route: 'panels', width: 1280, act: (p) => p.fill('#wash-cost', '5000') },
  {
    name: 'warnings filter',
    route: 'alerts',
    width: 1280,
    act: (p) => p.click('#alertFilter button >> nth=2'),
  },
  { name: 'site tab', route: 'settings', width: 1280, act: (p) => p.click('#tb-site') },
  { name: 'battery tab', route: 'settings', width: 1280, act: (p) => p.click('#tb-battery') },
  { name: 'battery tab', route: 'settings', width: 375, act: (p) => p.click('#tb-battery') },
  { name: 'tariff tab', route: 'settings', width: 1280, act: (p) => p.click('#tb-tariff') },
  { name: 'notifications tab', route: 'settings', width: 1280, act: (p) => p.click('#tb-notify') },
  { name: 'security tab', route: 'settings', width: 1280, act: (p) => p.click('#tb-security') },
  {
    name: 'unsaved changes bar',
    route: 'settings',
    width: 1280,
    act: (p) => p.fill('#p-name', 'Zaeem K'),
  },
  {
    name: 'delete dialog',
    route: 'settings',
    width: 1280,
    act: async (p) => {
      await p.click('#delBtn');
      await p.fill('#delIn', 'DELETE');
    },
  },
];

for (const { name, route: routeId, width, act } of scenarios) {
  test(`${routeId} · ${name} · ${width}px`, async ({ browser }) => {
    const route = ROUTES.find((r) => r.id === routeId);
    if (!route) throw new Error(`unknown route ${routeId}`);
    const newContext = () => browser.newContext({ reducedMotion: 'reduce', deviceScaleFactor: 1 });
    const ctxA = await newContext();
    const ctxB = await newContext();
    try {
      const pageA = await ctxA.newPage();
      const pageB = await ctxB.newPage();
      await openScreen(pageA, 'design', route, 'navy', width);
      await openScreen(pageB, 'port', route, 'navy', width);
      for (const page of [pageA, pageB]) {
        await act(page);
        await page.waitForTimeout(400);
      }
      const a = await shot(pageA);
      const b = await shot(pageB);
      const diff = await compare(a, b);
      const slug = `${routeId}-${name.replace(/\W+/g, '-')}-${width}`;
      if (diff.mismatched > tolerance(diff.total)) saveFailure(`state-${slug}`, a, b, diff);
      expect(
        { size: diff.sizeB, mismatched: diff.mismatched },
        `design ${diff.sizeA.join('x')} vs port ${diff.sizeB.join('x')}`,
      ).toEqual({ size: diff.sizeA, mismatched: 0 });
    } finally {
      await ctxA.close();
      await ctxB.close();
    }
  });
}
