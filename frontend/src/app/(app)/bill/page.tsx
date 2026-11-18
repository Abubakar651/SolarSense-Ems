import type { Metadata } from 'next';
import { BillView } from '@/features/bill/components/bill-view';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Bill & tariff' };

export default async function BillPage() {
  const defaults = await getServices().bill.getDefaults();
  return <BillView defaults={defaults} />;
}
