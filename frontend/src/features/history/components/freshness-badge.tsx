import { freshnessLabel, todayInKarachi } from '@/lib/freshness';
import type { Freshness } from '@/types/domain/history';

/** How current a history screen is: "Sample data", "Up to date" or "Data through <date>". */
export function FreshnessBadge({ freshness }: { freshness: Freshness }) {
  const { tone, text, title } = freshnessLabel(freshness, todayInKarachi(new Date()));

  return (
    <span className={`badge b-${tone}`} title={title} style={{ marginLeft: 6 }}>
      {text}
    </span>
  );
}
