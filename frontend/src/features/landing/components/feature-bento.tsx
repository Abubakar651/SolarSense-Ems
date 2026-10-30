import type { ReactNode } from 'react';
import { IconChip } from '@/components/ui/icon-chip';
import type { IconName } from '@/components/ui/icon-paths';
import { Reveal } from '@/components/ui/reveal';
import { cn } from '@/lib/cn';
import { fmt, pad } from '@/lib/format';
import type { Alert } from '@/types/domain/alerts';
import type { DayPlan } from '@/types/domain/energy';
import type { OutageData } from '@/types/domain/outage';
import type { SoilingData } from '@/types/domain/panels';
import type { MonthReport } from '@/types/domain/reports';
import { washAdvice } from '../../panels/view-model';
import { HoursBars } from './hours-bars';

interface CellProps {
  /** Reveal order within the grid. */
  index: number;
  className?: string;
  icon: IconName;
  title: string;
  body: string;
  children: ReactNode;
}

function Cell({ index, className, icon, title, body, children }: CellProps) {
  return (
    <Reveal as="article" className={cn('cell', className)} index={index}>
      <div>
        <IconChip icon={icon} decorative />
        <h3>{title}</h3>
        <p>{body}</p>
      </div>
      {children}
    </Reveal>
  );
}

const SampleTag = () => <span className="tag-sample">Sample data</span>;

const RISK_ROW_COUNT = 3;

interface FeatureBentoProps {
  plan: DayPlan;
  soiling: SoilingData;
  outage: OutageData;
  /** The newest monthly report. */
  report: MonthReport;
  latestAlert: Alert | undefined;
}

const totalOf = (report: MonthReport, label: string) =>
  report.totals.find((total) => total.label === label)?.value ?? '';

/** The six feature cards in an asymmetric grid, each with a small preview built from the sample data. */
export function FeatureBento({ plan, soiling, outage, report, latestAlert }: FeatureBentoProps) {
  const riskRows = outage.riskByHour
    .map((pct, hour) => ({ hour, pct }))
    .sort((a, b) => b.pct - a.pct)
    .slice(0, RISK_ROW_COUNT)
    .sort((a, b) => a.hour - b.hour);
  const topPct = Math.max(...outage.riskByHour);
  const reservePct = Math.round((plan.reserveFloorKwh / plan.batteryCapacityKwh) * 100);
  const advice = washAdvice(soiling, soiling.defaultWashCostPkr);
  const { tariff } = plan;

  return (
    <div className="bento">
      <Cell
        index={0}
        className="w2"
        icon="clock"
        title="Lower bills at peak hours"
        body="The battery is held for the expensive evening hours, and is never charged from the grid at peak rates."
      >
        <div className="mini">
          <div className="mini-h">
            <span>Usage by hour · peak highlighted</span>
            <SampleTag />
          </div>
          <HoursBars plan={plan} />
          <div className="hours-ax" aria-hidden="true">
            {['00:00', '06:00', '12:00', '18:00', '23:00'].map((t) => (
              <span key={t}>{t}</span>
            ))}
          </div>
        </div>
      </Cell>
      <Cell
        index={1}
        className="tall"
        icon="zap"
        title="Ready for load-shedding"
        body="See when the grid has failed, hour by hour, and keep a backup reserve you choose."
      >
        <div className="mini">
          <div className="mini-h">
            <span>Busiest outage hours</span>
            <SampleTag />
          </div>
          {riskRows.map(({ hour, pct }) => (
            <div className="risk-row" key={hour}>
              <span className="num">{`${pad(hour)}:00`}</span>
              <div className="bar">
                <i
                  style={{
                    width: `${(pct / topPct) * 100}%`,
                    ...(pct < topPct && { opacity: 0.4 }),
                  }}
                />
              </div>
              <span className="num">{`${pct}%`}</span>
            </div>
          ))}
          <div
            className="row between"
            style={{ marginTop: 'var(--sp-4)', fontSize: '.8125rem', color: 'var(--muted)' }}
          >
            <span>Backup reserve</span>
            <b className="num" style={{ color: 'var(--text)' }}>
              {`${reservePct}%`}
            </b>
          </div>
        </div>
      </Cell>
      <Cell
        index={2}
        icon="sun"
        title="Know when to wash the panels"
        body="We weigh the cost of dust against the cost of cleaning over the next two weeks, then say wash or wait."
      >
        <div className="mini">
          <div className="verdict">
            <IconChip icon="sun" tone="warn" />
            <div>
              <b>{advice.wash ? 'Wash the panels' : 'Wait for now'}</b>
              <span className="small muted">
                {advice.wash
                  ? 'Dust is costing more than cleaning.'
                  : `Cleaning would cost PKR ${fmt(-advice.netPkr)} more than the dust.`}
              </span>
            </div>
          </div>
        </div>
      </Cell>
      <Cell
        index={3}
        icon="bell"
        title="Alerts you can act on"
        body="Get told when the inverter reports a grid loss, and for how long."
      >
        <div className="mini">
          {latestAlert && (
            <div className="verdict">
              <IconChip icon="alert" tone={latestAlert.severity === 'crit' ? 'crit' : 'warn'} />
              <div>
                <b>{latestAlert.title}</b>
                <span className="small muted">
                  {`${latestAlert.when} · ${latestAlert.detail.split('. ')[0]}`}
                </span>
              </div>
            </div>
          )}
        </div>
      </Cell>
      <Cell
        index={4}
        icon="file"
        title="Monthly reports"
        body="Generation, grid use and savings, ready to download or email."
      >
        <div className="mini">
          <dl className="kv">
            <dt>Saved</dt>
            <dd className="num">{totalOf(report, 'Total saved')}</dd>
            <dt>Solar</dt>
            <dd className="num">{totalOf(report, 'Solar generated')}</dd>
            <dt>Grid import</dt>
            <dd className="num">{totalOf(report, 'Grid imported')}</dd>
          </dl>
          <p className="tag-sample" style={{ marginTop: 8 }}>
            {`${report.name} · ${report.coverage}`}
          </p>
        </div>
      </Cell>
      <Cell
        index={5}
        className="w2"
        icon="sliders"
        title="Your tariff, your rules"
        body="Enter your own rates and peak hours, and choose how cautious the battery should be."
      >
        <div className="mini">
          <div className="mini-h">
            <span>LESCO A-1 time-of-use rates</span>
            <SampleTag />
          </div>
          <dl className="kv">
            <dt>{`Peak · ${pad(plan.peakStartHour)}:00–${pad(plan.peakEndHour)}:00`}</dt>
            <dd className="num">{`PKR ${tariff.peakPkr.toFixed(2)} / kWh`}</dd>
            <dt>Off-peak</dt>
            <dd className="num">{`PKR ${tariff.offPeakPkr.toFixed(2)} / kWh`}</dd>
            <dt>Export credit</dt>
            <dd className="num">{`PKR ${tariff.exportPkr.toFixed(2)} / kWh`}</dd>
          </dl>
        </div>
      </Cell>
    </div>
  );
}
