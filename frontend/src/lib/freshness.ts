import type { Freshness } from '@/types/domain/history';
import { longDate } from './dates';

export interface FreshnessLabel {
  tone: 'ok' | 'warn';
  text: string;
  /** Tooltip with the exact day the figures run to. */
  title: string;
}

/** Today's date (YYYY-MM-DD) in the station's timezone, whatever the server's clock is set to. */
export function todayInKarachi(now: Date): string {
  // en-CA formats as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Karachi' }).format(now);
}

/** "2026-11-21" -> "2026-11-20". */
function dayBefore(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() - 1);
  return date.toISOString().slice(0, 10);
}

/**
 * The badge for a history screen. A history complete up to yesterday is current, because the backend
 * only counts finished days. `today` is the YYYY-MM-DD date in Asia/Karachi.
 */
export function freshnessLabel({ through, kind }: Freshness, today: string): FreshnessLabel {
  const title = `Figures run to ${longDate(through)}`;
  if (kind === 'sample') {
    return { tone: 'warn', text: 'Sample data', title: `${title}, from the recorded sample site` };
  }
  if (through >= dayBefore(today)) return { tone: 'ok', text: 'Up to date', title };
  return { tone: 'warn', text: `Data through ${longDate(through)}`, title };
}
