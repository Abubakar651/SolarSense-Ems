import { todayInKarachi } from '@/lib/freshness';
import type { MonthReport, ReportData } from '@/types/domain/reports';

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

/** A same-shaped report of all zeros, for the Reports screen while the site has none yet. */
export function zeroReportData(): ReportData {
  const today = new Date(`${todayInKarachi(new Date())}T00:00:00Z`);
  const name = `${MONTH_NAMES[today.getUTCMonth()]} ${today.getUTCFullYear()}`;
  const short = (MONTH_NAMES[today.getUTCMonth()] as string).slice(0, 3);
  const lastDay = today.getUTCDate();
  const dailyLabels = Array.from({ length: Math.max(lastDay, 2) }, (_, i) => String(i + 1));

  const month: MonthReport = {
    name,
    coverage: `Metered ${short} 1–${lastDay}`,
    totals: [
      { label: 'Solar generated', value: '0 kWh' },
      { label: 'Grid imported', value: '0 kWh' },
      { label: 'Exported', value: '0 kWh' },
      { label: 'Total saved', value: 'PKR 0' },
    ],
    dailyLabels,
    dailyValues: dailyLabels.map(() => 0),
    weeks: [],
  };

  return { site: '', months: [month], hourlyThrough: null };
}
