import type { Metadata } from 'next';
import { CardHeader } from '@/components/ui/card-header';
import { KpiCard, KpiStrip } from '@/components/ui/kpi-card';
import { PageHeader } from '@/components/ui/page-header';
import { dailyLossPkr, isDusty, lossPercent, paybackDays } from '@/features/panels/view-model';
import { fmt } from '@/lib/format';
import { PhotoCheck } from '@/features/panels/components/photo-check';
import { SoilingChart } from '@/features/panels/components/soiling-chart';
import { WashCalculator } from '@/features/panels/components/wash-calculator';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Panel health' };

const STATUS_BADGE_STYLE = { fontSize: '1rem', padding: '4px 14px' } as const;

export default async function PanelsPage() {
  const soiling = await getServices().panels.getSoiling();
  const lossPct = lossPercent(soiling);
  const dusty = isDusty(soiling);

  return (
    <section data-route="panels">
      <PageHeader title="Panel health">
        Dust and faults cost you electricity. Here is what it costs and whether cleaning is worth
        it.
      </PageHeader>
      <KpiStrip>
        <KpiCard
          label="Status"
          plain
          value={
            <span className={`badge ${dusty ? 'b-warn' : 'b-ok'}`} style={STATUS_BADGE_STYLE}>
              {dusty ? 'Dusty' : 'Clean'}
            </span>
          }
          sub={`Last washed ${soiling.lastWashed}`}
        />
        <KpiCard
          label="Output lost to dust"
          value={
            <>
              {lossPct}
              <small>%</small>
            </>
          }
          sub={`Model estimate as of ${soiling.asOf}`}
        />
        <KpiCard
          label="Energy lost per day"
          value={
            <>
              {soiling.dailyLossKwh.toFixed(1)}
              <small>kWh</small>
            </>
          }
          sub={`About PKR ${fmt(dailyLossPkr(soiling))} per day`}
        />
        <KpiCard
          label="Cleaning pays back in"
          value={
            <>
              {paybackDays(soiling, soiling.defaultWashCostPkr)}
              <small>days</small>
            </>
          }
          sub={`At PKR ${fmt(soiling.defaultWashCostPkr)} per cleaning`}
        />
      </KpiStrip>
      <div className="g-2 grid" style={{ marginTop: 'var(--sp-4)' }}>
        <WashCalculator soiling={soiling} />
        <div className="card">
          <CardHeader
            title="Dust loss since last wash"
            subtitle="Model estimate. Dashed line is the forecast without cleaning"
          />
          <SoilingChart soiling={soiling} />
        </div>
      </div>
      <PhotoCheck />
    </section>
  );
}
