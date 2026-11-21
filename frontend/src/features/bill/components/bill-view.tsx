import { PageHeader } from '@/components/ui/page-header';
import type { BillToolsDefaults } from '@/types/domain/tariff';
import { CompareCard } from './compare-card';
import { EstimateCard } from './estimate-card';

export function BillView({ defaults }: { defaults: BillToolsDefaults }) {
  return (
    <section data-route="bill">
      <PageHeader title="Bill & tariff" />
      <div className="grid">
        <EstimateCard defaults={defaults} />
        <CompareCard defaults={defaults} />
      </div>
    </section>
  );
}
