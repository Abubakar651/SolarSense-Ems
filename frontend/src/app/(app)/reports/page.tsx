import type { Metadata } from 'next';
import { ReportsView } from '@/features/reports/components/reports-view';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Reports' };

export default async function ReportsPage() {
  const report = await getServices().reports.getReport();

  return <ReportsView report={report} />;
}
