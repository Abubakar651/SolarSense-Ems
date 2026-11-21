import type { HistoryResult } from '@/types/domain/history';
import type { OutageData } from '@/types/domain/outage';
import type { OutageHistoryDto } from '../../http/dto';
import { fetchOutageHistory, toFreshness, toOutageRecords } from '../insights.http';
import { settingsHttp } from '../settings/settings.http';
import { buildOutage } from './outage.mock';
import type { OutageRepository } from './outage.repository';

/** The outage history as a screen result, "collecting" until the site has any recorded or logged day. */
export function outageResult(
  history: OutageHistoryDto,
  reservePct: number,
): HistoryResult<OutageData> {
  const { period_start: start, period_end: end } = history;
  if (start === null || end === null) {
    return { status: 'collecting', loggedDays: history.logged_days };
  }
  return {
    status: 'ready',
    data: buildOutage(toOutageRecords(history), { start, end }, end.slice(0, 7), reservePct),
    freshness: toFreshness(history, end),
  };
}

/** Recorded and logged outages from the API, summarised by the same builder as the sample data. */
export const outageHttp: OutageRepository = {
  async getOutage() {
    const [history, settings] = await Promise.all([
      fetchOutageHistory(),
      settingsHttp.getSettings(),
    ]);
    // The account's reserve floor: 15% unless the user changed it (Site.reserve_pct).
    return outageResult(history, settings.battery.reservePct);
  },
};
