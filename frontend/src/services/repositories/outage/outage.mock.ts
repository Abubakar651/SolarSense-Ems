import type { OutageData, OutageEvent } from '@/types/domain/outage';
import { STATION, TELEMETRY_DAY } from '../../mock/lhr-res-01';
import { OUTAGES, OUTAGE_PERIOD, type OutageRecord } from '../../mock/lhr-res-01-history';
import { durationLabel, longDate, shortDate } from '@/lib/dates';
import type { OutageRepository } from './outage.repository';

const RECENT_COUNT = 5;
const MS_PER_DAY = 86_400_000;
const RESERVE_PCT = (STATION.reserveFloorKwh / STATION.batteryKwh) * 100;

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
function outageShareByHour(): number[] {
  const days = (Date.parse(OUTAGE_PERIOD.end) - Date.parse(OUTAGE_PERIOD.start)) / MS_PER_DAY + 1;
  const daysByHour = Array.from({ length: 24 }, () => new Set<string>());
  for (const outage of OUTAGES) {
    for (const hour of hoursTouched(outage)) (daysByHour[hour] as Set<string>).add(outage[0]);
  }
  return daysByHour.map((set) => round1((set.size / days) * 100));
}

const hitReserve = ([, , , , , , socEnd]: OutageRecord) => socEnd !== null && socEnd <= RESERVE_PCT;

function toEvent(outage: OutageRecord): OutageEvent {
  const [date, start, , minutes, kwh] = outage;
  return {
    date: shortDate(date),
    started: start,
    duration: durationLabel(minutes),
    batteryUsed: `${kwh.toFixed(1)} kWh`,
    hitReserve: hitReserve(outage),
  };
}

function buildOutage(): OutageData {
  const month = TELEMETRY_DAY.slice(0, 7);
  const thisMonth = OUTAGES.filter(([date]) => date.startsWith(month));

  return {
    riskByHour: outageShareByHour(),
    recent: OUTAGES.slice(-RECENT_COUNT).reverse().map(toEvent),
    since: longDate(OUTAGE_PERIOD.start),
    totalCount: OUTAGES.length,
    thisMonth: {
      count: thisMonth.length,
      hours: round1(thisMonth.reduce((sum, [, , , minutes]) => sum + minutes, 0) / 60),
      hitReserve: thisMonth.filter(hitReserve).length,
    },
  };
}

export const outageMock: OutageRepository = {
  async getOutage() {
    return buildOutage();
  },
};
