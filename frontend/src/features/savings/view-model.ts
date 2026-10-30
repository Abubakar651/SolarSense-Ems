import { fmt } from '@/lib/format';
import type { SavingsSeries } from '@/types/domain/savings';

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
