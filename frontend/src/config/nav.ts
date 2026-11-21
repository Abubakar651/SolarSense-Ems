import type { IconName } from '@/components/ui/icon-paths';

export interface NavItem {
  href: string;
  label: string;
  icon: IconName;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const APP_NAV: NavGroup[] = [
  {
    label: 'Overview',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: 'home' },
      { href: '/plan', label: "Today's plan", icon: 'clock' },
      { href: '/energy', label: 'Energy', icon: 'grid' },
      { href: '/savings', label: 'Savings', icon: 'trend' },
      { href: '/bill', label: 'Bill & tariff', icon: 'wallet' },
    ],
  },
  {
    label: 'System',
    items: [
      { href: '/inverter', label: 'Live inverter', icon: 'battery' },
      { href: '/outage', label: 'Outage & backup', icon: 'zap' },
      { href: '/panels', label: 'Panel health', icon: 'sun' },
      { href: '/alerts', label: 'Alerts', icon: 'bell' },
    ],
  },
  {
    label: 'More',
    items: [
      { href: '/reports', label: 'Reports', icon: 'file' },
      { href: '/settings', label: 'Settings', icon: 'sliders' },
    ],
  },
];

const TITLES = new Map(
  APP_NAV.flatMap((group) => group.items).map((item) => [item.href, item.label]),
);

/** Top-bar title for an app route (falls back to the brand name). */
export function titleForPath(pathname: string): string {
  return TITLES.get(pathname) ?? 'SolarSense';
}
