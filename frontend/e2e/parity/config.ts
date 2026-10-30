import path from 'node:path';
import { pathToFileURL } from 'node:url';

export const THEMES = ['navy'] as const;
export type Theme = (typeof THEMES)[number];

/** The design still stores the navy theme under its old "blue" key. */
export const DESIGN_THEME_KEY: Record<Theme, string> = {
  navy: 'blue',
};

export const WIDTHS = [320, 375, 768, 1024, 1280, 1440] as const;
export const VIEWPORT_HEIGHT = 900;

export const DESIGN_URL = pathToFileURL(path.resolve(__dirname, '../../design/index.html')).href;
export const REPORT_DIR = path.resolve(__dirname, '../../parity-report');

export interface RouteSpec {
  id: string;
  /** Hash used by the design preview (`#/<hash>`). */
  designHash: string;
  /** Path in the Next.js app. */
  portPath: string;
  /** Flip to true as each screen lands in the port. */
  ported: boolean;
}

export const ROUTES: RouteSpec[] = [
  { id: 'landing', designHash: 'landing', portPath: '/', ported: true },
  { id: 'login', designHash: 'login', portPath: '/login', ported: true },
  { id: 'signup', designHash: 'signup', portPath: '/signup', ported: true },
  { id: 'verify', designHash: 'verify', portPath: '/verify', ported: true },
  { id: 'forgot', designHash: 'forgot', portPath: '/forgot', ported: true },
  { id: 'forgot-sent', designHash: 'forgot-sent', portPath: '/forgot/sent', ported: true },
  { id: 'reset', designHash: 'reset', portPath: '/reset', ported: true },
  { id: 'onboarding', designHash: 'onboarding', portPath: '/onboarding', ported: true },
  { id: 'dashboard', designHash: 'dashboard', portPath: '/dashboard', ported: true },
  { id: 'plan', designHash: 'plan', portPath: '/plan', ported: true },
  { id: 'savings', designHash: 'savings', portPath: '/savings', ported: true },
  { id: 'outage', designHash: 'outage', portPath: '/outage', ported: true },
  { id: 'panels', designHash: 'panels', portPath: '/panels', ported: true },
  { id: 'alerts', designHash: 'alerts', portPath: '/alerts', ported: true },
  { id: 'reports', designHash: 'reports', portPath: '/reports', ported: true },
  { id: 'settings', designHash: 'settings', portPath: '/settings', ported: true },
];

const csv = (v: string | undefined) => (v ? v.split(',').map((s) => s.trim()) : undefined);

/** Quick loop by default (navy, 375 + 1280); PARITY_FULL=1 runs every theme and width. */
export function matrix() {
  const full = !!process.env.PARITY_FULL;
  const themes =
    (csv(process.env.PARITY_THEMES) as Theme[] | undefined) ?? (full ? [...THEMES] : ['navy']);
  const widths = csv(process.env.PARITY_WIDTHS)?.map(Number) ?? (full ? [...WIDTHS] : [375, 1280]);
  const only = csv(process.env.PARITY_ROUTES);
  const everything = !!process.env.PARITY_ALL || !!process.env.PARITY_SELF;
  const routes = ROUTES.filter((r) => (only ? only.includes(r.id) : everything || r.ported));
  return { themes, widths, routes };
}
