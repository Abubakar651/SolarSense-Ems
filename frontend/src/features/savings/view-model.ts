import { fmt } from '@/lib/format';
import { todayInKarachi } from '@/lib/freshness';
import type { SavingsData, SavingsSeries } from '@/types/domain/savings';

const MONTH_NAMES = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];
const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function zeroSeries(labels: string[], title: string, word: string): SavingsSeries {
  return { labels, values: labels.map(() => 0), exportPkr: labels.map(() => 0), title, word };
}

/** A same-shaped savings history of all zeros, for the Savings screen while the site has none yet. */
export function zeroSavingsData(): SavingsData {
  const today = new Date(`${todayInKarachi(new Date())}T00:00:00Z`);
  const DAY_MS = 86_400_000;
  const weekLabels = Array.from(
    { length: 7 },
    (_, i) => WEEKDAYS[new Date(today.getTime() - (6 - i) * DAY_MS).getUTCDay()] as string,
  );
  const monthLabels = Array.from({ length: 30 }, (_, i) =>
    String(new Date(today.getTime() - (29 - i) * DAY_MS).getUTCDate()),
  );
  const yearLabels = Array.from(
    { length: 12 },
    (_, i) =>
      MONTH_NAMES[
        (((today.getUTCMonth() - (11 - i)) % 12) + 12) % 12
      ] as string,
  );

  return {
    week: zeroSeries(weekLabels, 'Daily savings', 'day'),
    month: zeroSeries(monthLabels, 'Daily savings', 'day'),
    year: zeroSeries(yearLabels, 'Monthly savings', 'month'),
    currentMonth: {
      label: `${MONTH_NAMES[today.getUTCMonth()]} 1–${today.getUTCDate()}`,
      costPkr: 0,
      withoutSolarPkr: 0,
      selfPoweredPct: 0,
    },
    exportRatePkr: 0,
  };
}

export interface SavingsSummary {
  total: string;
  average: string;
  exportCredit: string;
  breakdown: { label: string; amount: string; widthPct: number }[];
  tableRows: string[][];
  /** Heading of the first table column ("Day" / "Month"). */
  periodLabel: string;
}

export function savingsSummary(series: SavingsSeries): SavingsSummary {
  const sum = (values: number[]) => values.reduce((a, b) => a + b, 0);
  const total = sum(series.values);
  const exportTotal = sum(series.exportPkr);
  const sources = [
    { label: 'Solar and battery used at home', pkr: total - exportTotal },
    { label: 'Export credit', pkr: exportTotal },
  ];

  return {
    total: `PKR ${fmt(total)}`,
    average: `Average PKR ${fmt(total / series.values.length)} per ${series.word}`,
    exportCredit: `PKR ${fmt(exportTotal)}`,
    breakdown: sources.map(({ label, pkr }) => {
      const share = total === 0 ? 0 : pkr / total;
      return {
        label,
        amount: `PKR ${fmt(pkr)} · ${Math.round(share * 100)}%`,
        widthPct: share * 100,
      };
    }),
    tableRows: series.values.map((value, i) => [series.labels[i] as string, fmt(value)]),
    periodLabel: series.word.charAt(0).toUpperCase() + series.word.slice(1),
  };
}
