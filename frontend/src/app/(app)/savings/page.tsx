import type { Metadata } from 'next';
import { SavingsView } from '@/features/savings/components/savings-view';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Savings' };

export default async function SavingsPage() {
  const data = await getServices().savings.getSavings();
  return <SavingsView data={data} />;
}
