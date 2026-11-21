/** How current a history screen's figures are. */
export interface Freshness {
  /** Last day the figures cover (YYYY-MM-DD). */
  through: string;
  /** sample: the bundled demo data; recorded: the station's recorded dataset; logged: this site's own inverter log. */
  kind: 'sample' | 'recorded' | 'logged';
}

/**
 * What a history repository returns: the figures with their freshness, "collecting" while the site's
 * inverter log is too short to show anything yet, or "unavailable" when the site has no such history.
 */
export type HistoryResult<T> =
  | { status: 'ready'; data: T; freshness: Freshness }
  | { status: 'collecting'; loggedDays: number }
  | { status: 'unavailable' };

export type HistoryNotReady = Exclude<HistoryResult<unknown>, { status: 'ready' }>;
