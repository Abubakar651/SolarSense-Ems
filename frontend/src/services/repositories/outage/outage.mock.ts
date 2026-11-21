import type { OutageData, OutageEvent } from '@/types/domain/outage';
import { STATION, TELEMETRY_DAY } from '../../mock/lhr-res-01';
import { OUTAGES, OUTAGE_PERIOD, type OutageRecord } from '../../mock/lhr-res-01-history';
import { durationLabel, longDate, shortDate } from '@/lib/dates';
import type { OutageRepository } from './outage.repository';

const RECENT_COUNT = 5;
const MS_PER_DAY = 86_400_000;
/** The sample site's reserve floor as a percentage (15%), used by the sample data and as the default. */
const SAMPLE_RESERVE_PCT = (STATION.reserveFloorKwh / STATION.batteryKwh) * 100;

const clock = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));
const round1 = (value: number) => Math.round(value * 10) / 10;

/** Hours of the day (0-23) an outage touched; an outage that crosses midnight wraps round. */
function hoursTouched([, start, end]: OutageRecord): number[] {
  const first = Math.floor(clock(start) / 60);
  const last = Math.floor(clock(end) / 60);
  const count = ((last - first + 24) % 24) + 1;
  return Array.from({ length: count }, (_, i) => (first + i) % 24);
}

/** Percent of recorded days on which an outage was in progress during each hour. */
function outageShareByHour(outages: readonly OutageRecord[], period: OutagePeriod): number[] {
  const days = (Date.parse(period.end) - Date.parse(period.start)) / MS_PER_DAY + 1;
  const daysByHour = Array.from({ length: 24 }, () => new Set<string>());
  for (const outage of outages) {
    for (const hour of hoursTouched(outage)) (daysByHour[hour] as Set<string>).add(outage[0]);
  }
  return daysByHour.map((set) => round1((set.size / days) * 100));
}

const hitReserve = ([, , , , , , socEnd]: OutageRecord, reservePct: number) =>
  socEnd !== null && socEnd <= reservePct;

function toEvent(outage: OutageRecord, reservePct: number): OutageEvent {
  const [date, start, , minutes, kwh] = outage;
  return {
    date: shortDate(date),
    started: start,
    duration: durationLabel(minutes),
    batteryUsed: `${kwh.toFixed(1)} kWh`,
    hitReserve: hitReserve(outage, reservePct),
  };
}

/** First and last day of the recorded outage history (YYYY-MM-DD). */
export interface OutagePeriod {
  start: string;
  end: string;
}

/**
 * The Outage screen from recorded outages (oldest first). Shared by the sample data and the API
 * repository, so both show the same figures. `month` is the "this month" being summarised (YYYY-MM)
 * and `reservePct` the account's reserve floor, the level an outage is measured against.
 */
export function buildOutage(
  outages: readonly OutageRecord[],
  period: OutagePeriod,
  month: string,
  reservePct: number = SAMPLE_RESERVE_PCT,
): OutageData {
  const thisMonth = outages.filter(([date]) => date.startsWith(month));

  return {
    riskByHour: outageShareByHour(outages, period),
    recent: outages
      .slice(-RECENT_COUNT)
      .reverse()
      .map((outage) => toEvent(outage, reservePct)),
    since: longDate(period.start),
    totalCount: outages.length,
    thisMonth: {
      count: thisMonth.length,
      hours: round1(thisMonth.reduce((sum, [, , , minutes]) => sum + minutes, 0) / 60),
      hitReserve: thisMonth.filter((outage) => hitReserve(outage, reservePct)).length,
    },
  };
}

export const outageMock: OutageRepository = {
  async getOutage() {
    return {
      status: 'ready',
      data: buildOutage(OUTAGES, OUTAGE_PERIOD, TELEMETRY_DAY.slice(0, 7)),
      freshness: { through: TELEMETRY_DAY, kind: 'sample' },
    };
  },
};
