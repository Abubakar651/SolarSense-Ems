import { Donut } from '@/components/charts/donut';
import { CardHeader } from '@/components/ui/card-header';
import { fmt } from '@/lib/format';
import { BASIS_LABEL, consumptionSplit, generationSplit, type TodayEnergy } from '../today';

const kwh = (value: number) => `${value.toFixed(1)} kWh`;

interface TodayEnergyCardProps {
  today: TodayEnergy;
  /** Export credit per kWh; adds an export-credit tile when given. */
  exportRatePkr?: number;
}

/** The day's totals as tiles, and two rings: where the solar went and where the power came from. */
export function TodayEnergyCard({ today, exportRatePkr }: TodayEnergyCardProps) {
  const generation = generationSplit(today);
  const consumption = consumptionSplit(today);
  const tiles: [string, string][] = [
    ['Generated', kwh(today.generationKwh)],
    ['Used', kwh(today.consumptionKwh)],
    ['Imported', kwh(today.importKwh)],
    ['Exported', kwh(today.exportKwh)],
  ];
  if (exportRatePkr !== undefined) {
    tiles.push(['Export credit', `PKR ${fmt(today.exportKwh * exportRatePkr)}`]);
  }
  if (today.battery !== null) {
    tiles.push(['Charged', kwh(today.battery.chargedKwh)]);
    tiles.push(['Discharged', kwh(today.battery.dischargedKwh)]);
  }

  return (
    <div className="card">
      <CardHeader
        title="Today's energy"
        action={<span className="badge b-neutral">{BASIS_LABEL[today.basis]}</span>}
      />
      <dl className="e-tiles">
        {tiles.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd className="num">{value}</dd>
          </div>
        ))}
      </dl>
      <div className="e-donuts">
        <Donut
          ariaLabel={`Solar generated: ${generation.firstPct}% used on site, the rest exported.`}
          center={`${generation.firstPct}%`}
          centerLabel="used on site"
          format={kwh}
          segments={[
            { label: 'Used on site', value: generation.firstKwh, color: 'var(--accent)' },
            { label: 'Exported', value: generation.secondKwh, color: 'var(--tint-3)' },
          ]}
        />
        <Donut
          ariaLabel={`Home usage: ${consumption.firstPct}% from solar and battery, the rest from the grid.`}
          center={`${consumption.firstPct}%`}
          centerLabel="self-powered"
          format={kwh}
          segments={[
            { label: 'Solar & battery', value: consumption.firstKwh, color: 'var(--accent)' },
            { label: 'Grid', value: consumption.secondKwh, color: 'var(--primary)' },
          ]}
        />
      </div>
    </div>
  );
}
