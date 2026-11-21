'use client';

import Link from 'next/link';
import { PlanChart } from '@/components/charts/plan-chart';
import { CardHeader } from '@/components/ui/card-header';
import { CountUp } from '@/components/ui/count-up';
import { KpiCard, KpiStrip } from '@/components/ui/kpi-card';
import { TodayEnergyCard } from '@/features/energy/components/today-energy-card';
import { todayFromPlan, todayFromReading } from '@/features/energy/today';
import { useSampleClock } from '@/providers/sample-clock-provider';
import type { DayPlan } from '@/types/domain/energy';
import type { InverterReading } from '@/types/domain/inverter';
import { fmt, pad } from '@/lib/format';
import type { AttentionItem } from '../attention';
import { useInverterReading } from '../use-inverter-reading';
import { dashboardSnapshot, dayFacts, forecastNote } from '../view-model';
import { AttentionList } from './attention-list';
import { ChartLegend } from './chart-legend';
import { EnergyFlowCard } from './energy-flow-card';

const OFFLINE_VALUE = <span aria-label="Not available">—</span>;

interface DashboardLiveProps {
  plan: DayPlan;
  attention: AttentionItem[];
  /** The inverter at page load; null while the plan replays sample data. */
  initialReading: InverterReading | null;
  readInverter: () => Promise<InverterReading>;
}

/** Everything on the dashboard that follows the clock and the inverter. */
export function DashboardLive({
  plan,
  attention,
  initialReading,
  readInverter,
}: DashboardLiveProps) {
  const now = useSampleClock();
  const reading = useInverterReading(initialReading, readInverter);
  const snap = dashboardSnapshot(plan, now, reading);
  const facts = dayFacts(plan);
  const offline = snap.source === 'offline';
  const note = forecastNote(plan);
  const today =
    reading?.status === 'online'
      ? todayFromReading(reading.data, reading.isSample)
      : todayFromPlan(plan);

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
          sub="vs no solar or battery"
        />
        <KpiCard
          label="Solar now"
          icon="sun"
          value={
            offline ? (
              OFFLINE_VALUE
            ) : (
              <>
                <CountUp value={snap.solarKw.toFixed(1)} />
                <small>kW</small>
              </>
            )
          }
          sub={
            offline
              ? 'Inverter offline'
              : `Peak ${facts.peakSolar.kw.toFixed(1)} kW at ${pad(facts.peakSolar.hour)}:00`
          }
        />
        <KpiCard
          label="Battery"
          icon="battery"
          value={
            offline ? (
              OFFLINE_VALUE
            ) : (
              <>
                <CountUp value={String(snap.soc)} />
                <small>%</small>
              </>
            )
          }
          sub={offline ? 'Inverter offline' : snap.batterySub}
          subId="k-soc-sub"
        />
        <KpiCard
          label="Backup time"
          icon="clock"
          value={
            offline ? (
              OFFLINE_VALUE
            ) : (
              <>
                <CountUp value={snap.backupHours} />
                <small>hours</small>
              </>
            )
          }
          sub={offline ? 'Inverter offline' : undefined}
        />
      </KpiStrip>

      <div className="plate" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="plate-h">
          <div>
            <h2>Today</h2>
            {note && (
              <span className="badge b-warn" title={note}>
                Partial history
                <span className="sr-only">{`. ${note}`}</span>
              </span>
            )}
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
        <EnergyFlowCard snap={snap} />
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
            <div
              className="bar"
              style={{ marginTop: 14 }}
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

      <div style={{ marginTop: 'var(--sp-4)' }}>
        <TodayEnergyCard today={today} exportRatePkr={plan.tariff.exportPkr} />
      </div>
    </>
  );
}
