import type { Metadata } from 'next';
import { ReportsView } from '@/features/reports/components/reports-view';
import { zeroReportData } from '@/features/reports/view-model';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Reports' };

export default async function ReportsPage() {
  const { reports } = getServices();
  const [result, emailPrefs] = await Promise.all([reports.getReport(), reports.getEmailPrefs()]);

  if (result.status !== 'ready') {
    return <ReportsView report={zeroReportData()} emailPrefs={emailPrefs} notReady={result} />;
  }
  return <ReportsView report={result.data} freshness={result.freshness} emailPrefs={emailPrefs} />;
}
