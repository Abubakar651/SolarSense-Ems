import type { Metadata } from 'next';
import Link from 'next/link';
import { CardHeader } from '@/components/ui/card-header';
import { ChartTable, DataTable } from '@/components/ui/data-table';
import { Icon } from '@/components/ui/icon';
import { KpiCard, KpiStrip } from '@/components/ui/kpi-card';
import { PageHeader } from '@/components/ui/page-header';
import { pad } from '@/lib/format';
import { BackupKpi } from '@/features/outage/components/backup-kpi';
import { RiskChart } from '@/features/outage/components/risk-chart';
import { RISK_LABEL, riskLevel } from '@/features/outage/view-model';
import { getServices } from '@/services';

export const metadata: Metadata = { title: 'Outage & backup' };

const RISK_BADGE_STYLE = { fontSize: '1rem', padding: '4px 14px' } as const;
const SMALL_ICON = { width: 14, height: 14 } as const;
const RISK_BADGE = { 0: 'b-ok', 1: 'b-warn', 2: 'b-bad' } as const;

export default async function OutagePage() {
  const { energy, outage } = getServices();
  const [plan, data] = await Promise.all([energy.getDayPlan(), outage.getOutage()]);
  const levels = data.riskByHour.map(riskLevel);
  const busiestHour = data.riskByHour.indexOf(Math.max(...data.riskByHour));
  const reservePct = Math.round((plan.reserveFloorKwh / plan.batteryCapacityKwh) * 100);
  const { thisMonth } = data;

  return (
    <section data-route="outage">
      <PageHeader title="Outage & backup">
        When the grid has failed before and how ready your battery is.
      </PageHeader>
      <KpiStrip>
        <KpiCard
          label="Outage risk"
          plain
          value={
            <span
              className={`badge ${RISK_BADGE[levels[busiestHour] as 0 | 1 | 2]}`}
              style={RISK_BADGE_STYLE}
            >
              {RISK_LABEL[levels[busiestHour] as 0 | 1 | 2]}
            </span>
          }
          sub={`Busiest hour is ${pad(busiestHour)}:00, with an outage on ${data.riskByHour[busiestHour]}% of days`}
        />
        <KpiCard
          label="Reserve held"
          value={
            <>
              {reservePct}
              <small>%</small>
            </>
          }
          sub={
            <>
              Never used for savings. <Link href="/settings">Change in settings</Link>
            </>
          }
        />
        <BackupKpi plan={plan} />
        <KpiCard
          label="Outages this month"
          value={String(thisMonth.count)}
          sub={`Total ${thisMonth.hours} hours, ${
            thisMonth.hitReserve === 0
              ? 'all covered by battery'
              : `battery hit reserve ${thisMonth.hitReserve} time${thisMonth.hitReserve === 1 ? '' : 's'}`
          }`}
        />
      </KpiStrip>
      <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
        <CardHeader
          title="Outages by hour of day"
          subtitle={`Share of days since ${data.since} with an outage of 15 minutes or more in progress (${data.totalCount} outages)`}
        />
        <div className="legend">
          <span>
            <i className="k-low" />
            Low (under 15%)
          </span>
          <span>
            <i className="k-med" />
            Medium (15–30%)
          </span>
          <span>
            <i className="k-high" />
            High (over 30%)
          </span>
        </div>
        <RiskChart riskByHour={data.riskByHour} />
        <ChartTable
          columns={[{ label: 'Hour' }, { label: 'Risk', right: true }, { label: 'Level' }]}
          rows={data.riskByHour.map((pct, hour) => [
            `${pad(hour)}:00`,
            `${pct}%`,
            RISK_LABEL[levels[hour] as 0 | 1 | 2],
          ])}
        />
      </div>
      <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
        <CardHeader title="Recent outages" />
        <DataTable
          columns={[
            { label: 'Date' },
            { label: 'Started' },
            { label: 'Duration', right: true },
            { label: 'Battery used', right: true },
            { label: 'Result' },
          ]}
          rows={data.recent.map((event) => [
            event.date,
            event.started,
            event.duration,
            event.batteryUsed,
            event.hitReserve ? (
              <span className="badge b-warn">
                <Icon name="alert" style={SMALL_ICON} />
                Battery hit reserve
              </span>
            ) : (
              <span className="badge b-ok">
                <Icon name="check" style={SMALL_ICON} />
                Fully covered
              </span>
            ),
          ])}
        />
      </div>
    </section>
  );
}
