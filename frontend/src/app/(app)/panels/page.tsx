import type { Metadata } from 'next';
import { CardHeader } from '@/components/ui/card-header';
import { CollectingBadge } from '@/features/history/components/collecting-badge';
import { FreshnessBadge } from '@/features/history/components/freshness-badge';
import { KpiCard, KpiStrip } from '@/components/ui/kpi-card';
import { PageHeader } from '@/components/ui/page-header';
import {
  collectingMessage,
  dailyLossPkr,
  isDusty,
  lastCleanedLabel,
  lossPercent,
  paybackDays,
  washedToday,
  zeroSoilingData,
} from '@/features/panels/view-model';
import { fmt } from '@/lib/format';
import { todayInKarachi } from '@/lib/freshness';
import { PhotoCheck } from '@/features/panels/components/photo-check';
import { SoilingChart } from '@/features/panels/components/soiling-chart';
import { WashButton } from '@/features/panels/components/wash-button';
import { WashCalculator } from '@/features/panels/components/wash-calculator';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Panel health' };

const STATUS_BADGE_STYLE = { fontSize: '1rem', padding: '4px 14px' } as const;
const UNAVAILABLE_MESSAGE = 'Sunlight data is unavailable right now. Try again later.';

export default async function PanelsPage() {
  const result = await getServices().panels.getSoiling();
  const ready = result.status === 'ready';
  const soiling = ready ? result.data : zeroSoilingData();
  const lossPct = lossPercent(soiling);
  const dusty = isDusty(soiling);
  const payback = paybackDays(soiling, soiling.defaultWashCostPkr);
  const washedTodayAlready =
    result.status === 'collecting' && washedToday(result, todayInKarachi(new Date()));
  const notReadyBadge =
    result.status === 'collecting' ? (
      <CollectingBadge
        result={{ status: 'collecting', loggedDays: result.loggedDays }}
        unavailableMessage={collectingMessage(result)}
      />
    ) : result.status === 'unavailable' ? (
      <CollectingBadge result={result} unavailableMessage={UNAVAILABLE_MESSAGE} />
    ) : null;

  return (
    <section data-route="panels">
      <PageHeader title="Panel health">
        {ready ? <FreshnessBadge freshness={result.freshness} /> : notReadyBadge}
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
          sub={lastCleanedLabel(soiling)}
        />
        <KpiCard
          label="Output lost to dust"
          value={
            <>
              {lossPct}
              <small>%</small>
            </>
          }
          sub={`As of ${soiling.asOf}`}
        />
        <KpiCard
          label="Energy lost per day"
          value={
            <>
              {soiling.dailyLossKwh.toFixed(1)}
              <small>kWh</small>
            </>
          }
          sub={`≈ PKR ${fmt(dailyLossPkr(soiling))}/day`}
        />
        <KpiCard
          label="Cleaning pays back in"
          value={
            payback === null ? (
              '–'
            ) : (
              <>
                {payback}
                <small>days</small>
              </>
            )
          }
          sub={
            payback === null
              ? 'No dust cost yet'
              : `PKR ${fmt(soiling.defaultWashCostPkr)} per wash`
          }
        />
      </KpiStrip>
      <div className="g-2 grid" style={{ marginTop: 'var(--sp-4)' }}>
        <WashCalculator soiling={soiling} />
        <div className="card">
          <CardHeader
            title={
              soiling.cleanEvent === 'rain'
                ? 'Dust loss since the rain'
                : 'Dust loss since last wash'
            }
            subtitle="Dashed = without cleaning"
            action={<WashButton washedToday={washedTodayAlready} />}
          />
          <SoilingChart soiling={soiling} />
        </div>
      </div>
      <PhotoCheck />
    </section>
  );
}
