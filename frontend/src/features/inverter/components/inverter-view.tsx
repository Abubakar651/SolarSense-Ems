import Link from 'next/link';
import type { ReactNode } from 'react';
import { CardHeader } from '@/components/ui/card-header';
import { ErrorState } from '@/components/ui/error-state';
import { KpiCard, KpiStrip } from '@/components/ui/kpi-card';
import { PageHeader } from '@/components/ui/page-header';
import { FlowDiagram } from '@/components/charts/flow-diagram';
import { TodayEnergyCard } from '@/features/energy/components/today-energy-card';
import { todayFromReading } from '@/features/energy/today';
import type { InverterReading } from '@/types/domain/inverter';
import { batteryFlow, flowValues, gridFlow, reading, readingTime } from '../view-model';

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="row between small" style={{ padding: '6px 0' }}>
      <span className="muted">{label}</span>
      <b className="num">{children}</b>
    </div>
  );
}

const kw = (watts: number) => (watts / 1000).toFixed(2);

export function InverterView({ result }: { result: InverterReading }) {
  if (result.status === 'offline') {
    return (
      <ErrorState
        title="Inverter offline"
        message={result.message}
        action={
          <Link className="btn btn-primary" href="/inverter">
            Try again
          </Link>
        }
      />
    );
  }

  const { data, isSample } = result;
  return (
    <section data-route="inverter">
      <PageHeader
        title="Live inverter"
        actions={
          <span className={isSample ? 'badge b-neutral' : 'badge b-ok'}>
            {isSample ? 'Sample data' : 'Live'}
          </span>
        }
      >
        {`Updated ${readingTime(data.timestamp)}`}
      </PageHeader>
      <KpiStrip>
        <KpiCard
          label="Battery"
          icon="battery"
          lead
          value={
            <>
              {Math.round(data.batterySocPct)}
              <small>%</small>
            </>
          }
          sub={batteryFlow(data.batteryPowerW)}
        />
        <KpiCard
          label="Solar now"
          icon="sun"
          value={
            <>
              {kw(data.totalPvPowerW)}
              <small>kW</small>
            </>
          }
          sub={`String 1 ${kw(data.pv1PowerW)} kW · string 2 ${kw(data.pv2PowerW)} kW`}
        />
        <KpiCard
          label="Home usage"
          icon="home"
          value={
            <>
              {kw(data.houseConsumptionW)}
              <small>kW</small>
            </>
          }
        />
        <KpiCard
          label="Grid"
          icon="grid"
          plain
          value={data.isGridConnected ? 'Connected' : 'Down'}
          sub={gridFlow(data)}
        />
      </KpiStrip>
      <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
        <CardHeader title="Energy flow" />
        <div className="flow">
          <FlowDiagram {...flowValues(data)} />
        </div>
      </div>
      <div className="g-3 grid" style={{ marginTop: 'var(--sp-4)' }}>
        <div className="card">
          <CardHeader title="Battery" />
          <Detail label="Mode">{data.batteryMode}</Detail>
          <Detail label="Voltage">{reading(data.batteryVoltageV, 'V')}</Detail>
          <Detail label="Current">{reading(data.batteryCurrentA, 'A')}</Detail>
          <Detail label="Health">{reading(data.batterySohPct, '%', 0)}</Detail>
          <Detail label="Temperature">{reading(data.batteryTempC, '°C')}</Detail>
        </div>
        <div className="card">
          <CardHeader title="Grid and backup" />
          <Detail label="Grid mode">{data.gridMode}</Detail>
          <Detail label="Voltage">{reading(data.gridVoltageV, 'V', 0)}</Detail>
          <Detail label="Frequency">{reading(data.gridFrequencyHz, 'Hz')}</Detail>
          <Detail label="Backup voltage">{reading(data.backupVoltageV, 'V', 0)}</Detail>
          <Detail label="Backup power">
            {data.backupPowerW === null ? '—' : `${kw(data.backupPowerW)} kW`}
          </Detail>
        </div>
        <div className="card">
          <CardHeader title="Inverter" />
          <Detail label="Model">{data.modelName}</Detail>
          <Detail label="Serial">{data.serialNumber}</Detail>
          <Detail label="Work mode">{data.workMode}</Detail>
          <Detail label="Air temperature">{reading(data.inverterTempAirC, '°C')}</Detail>
          <Detail label="Heatsink temperature">{reading(data.inverterTempRadiatorC, '°C')}</Detail>
        </div>
      </div>
      <div style={{ marginTop: 'var(--sp-4)' }}>
        <TodayEnergyCard today={todayFromReading(data, isSample)} />
      </div>
    </section>
  );
}
