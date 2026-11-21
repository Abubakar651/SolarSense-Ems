import { historyNotReadyLabel } from '@/lib/history';
import type { HistoryNotReady } from '@/types/domain/history';

/** Marks a screen's figures as placeholders while the site's data isn't ready yet. */
export function CollectingBadge({
  result,
  unavailableMessage,
}: {
  result: HistoryNotReady;
  unavailableMessage?: string;
}) {
  const text = historyNotReadyLabel(result, unavailableMessage);
  return (
    <span className="badge b-warn" title={text} style={{ marginLeft: 6 }}>
      {result.status === 'collecting' ? 'Collecting data' : 'Not available'}
    </span>
  );
}
