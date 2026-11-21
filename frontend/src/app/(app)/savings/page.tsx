import type { Metadata } from 'next';
import { SavingsView } from '@/features/savings/components/savings-view';
import { zeroSavingsData } from '@/features/savings/view-model';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Savings' };

export default async function SavingsPage() {
  const result = await getServices().savings.getSavings();
  if (result.status !== 'ready') {
    return <SavingsView data={zeroSavingsData()} notReady={result} />;
  }
  return <SavingsView data={result.data} freshness={result.freshness} />;
}
