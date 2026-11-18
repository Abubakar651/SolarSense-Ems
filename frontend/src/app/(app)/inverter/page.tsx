import type { Metadata } from 'next';
import { InverterView } from '@/features/inverter/components/inverter-view';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Live inverter' };

export default async function InverterPage() {
  const result = await getServices().inverter.getLive();
  return <InverterView result={result} />;
}
