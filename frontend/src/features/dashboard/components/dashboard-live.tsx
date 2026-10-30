'use client';

import Link from 'next/link';
import { FlowDiagram } from '@/components/charts/flow-diagram';
import { PlanChart } from '@/components/charts/plan-chart';
import { CardHeader } from '@/components/ui/card-header';
import { CountUp } from '@/components/ui/count-up';
import { KpiCard, KpiStrip } from '@/components/ui/kpi-card';
import { useSampleClock } from '@/providers/sample-clock-provider';
import type { DayPlan } from '@/types/domain/energy';
import { fmt, pad } from '@/lib/format';
import type { AttentionItem } from '../attention';
import { dashboardSnapshot, dayFacts } from '../view-model';
import { AttentionList } from './attention-list';
import { ChartLegend } from './chart-legend';

/** Everything on the dashboard that follows the sample clock. */
export function DashboardLive({ plan, attention }: { plan: DayPlan; attention: AttentionItem[] }) {
  const now = useSampleClock();
  const snap = dashboardSnapshot(plan, now);
  const facts = dayFacts(plan);

  return (
    <>
      <KpiStrip>
        <KpiCard
          label="Saved today"
          icon="wallet"
          lead
          value={
            <>
              <small style={{ margin: '0 4px 0 0' }}>PKR</small>
              <CountUp value={fmt(facts.savedTodayPkr)} />
            </>
          }
          sub="Today's plan vs no solar or battery"
        />
        <KpiCard
          label="Solar now"
          icon="sun"
          value={
            <>
              <CountUp value={snap.solarKw.toFixed(1)} />
              <small>kW</small>
            </>
          }
          sub={`Hourly peak: ${facts.peakSolar.kw.toFixed(1)} kW at ${pad(facts.peakSolar.hour)}:00`}
        />
        <KpiCard
          label="Battery"
          icon="battery"
          value={
            <>
              <CountUp value={String(snap.soc)} />
              <small>%</small>
            </>
          }
          sub={snap.batterySub}
          subId="k-soc-sub"
        />
        <KpiCard
          label="Backup time"
          icon="clock"
          value={
            <>
              <CountUp value={snap.backupHours} />
              <small>hours</small>
            </>
          }
          sub="If the grid goes down now"
        />
      </KpiStrip>

      <div className="plate" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="plate-h">
          <div>
            <h2>Today</h2>
          </div>
          <ChartLegend />
        </div>
        <PlanChart
          id="chart-dash"
          readoutId="dash-readout"
          series={plan}
          now={now}
          height={{ narrow: 280, wide: 330 }}
        />
      </div>

      <div className="g-21 grid" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="card">
          <CardHeader
            title="Energy flow"
            subtitle="Where your power is going right now"
            action={
              <span className="badge b-ok">
                <span className="dot live" />
                Grid connected
              </span>
            }
          />
          <div className="flow" id="flow">
            <FlowDiagram {...snap} />
          </div>
          <p className="small muted" id="flow-sum" style={{ textAlign: 'center', marginTop: 8 }}>
            {snap.flowSummary}
          </p>
        </div>
        <div className="grid" style={{ alignContent: 'start' }}>
          <div className="card">
            <CardHeader
              title="Next peak"
              style={{ marginBottom: 8 }}
              action={<span className="badge b-info">{`Starts ${facts.peakStart}`}</span>}
            />
            <div className="big num" id="peak-cd">
              {snap.peakCountdown}
            </div>
            <p className="small muted" style={{ margin: '6px 0 14px' }}>
              {`until the evening rate (${facts.rateNote})`}
            </p>
            <div
              className="bar"
              role="img"
              id="peak-bar"
              aria-label={`Battery is ${snap.soc} percent full ahead of peak hours`}
            >
              <i style={{ width: `${snap.soc}%` }} />
            </div>
            <p className="small muted" style={{ marginTop: 8 }} id="peak-note">
              {snap.peakNote}
            </p>
          </div>
          <div className="card">
            <CardHeader
              title="Needs your attention"
              style={{ marginBottom: 0 }}
              action={
                <Link className="btn btn-ghost btn-sm" href="/alerts">
                  All alerts
                </Link>
              }
            />
            <AttentionList items={attention} />
          </div>
        </div>
      </div>
    </>
  );
}
