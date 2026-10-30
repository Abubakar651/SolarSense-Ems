import { cn } from '@/lib/cn';
import { ICON_PATHS, type IconName } from '@/components/ui/icon-paths';

export interface FlowValues {
  solarKw: number;
  loadKw: number;
  chargeKw: number;
  gridKw: number;
  exportKw: number;
  soc: number;
}

const MAX_KW_FOR_SPEED = 6;

/** Dashes travel faster the more power flows (1.8s at idle down to 0.6s at 6 kW). */
const dashDuration = (kw: number) => (1.8 - Math.min(kw, MAX_KW_FOR_SPEED) * 0.2).toFixed(2);

function Node({ x, y, icon, on }: { x: number; y: number; icon: IconName; on: boolean }) {
  return (
    <>
      <rect className={cn('node', on && 'on')} x={x - 30} y={y - 30} width="60" height="60" />
      <g
        transform={`translate(${x - 12} ${y - 12})`}
        className="ic"
        dangerouslySetInnerHTML={{ __html: ICON_PATHS[icon] }}
      />
    </>
  );
}

function Flow({
  d,
  on,
  reverse = false,
  kw = 0,
}: {
  d: string;
  on: boolean;
  reverse?: boolean;
  kw?: number;
}) {
  return (
    <path
      className={cn('ln', on && 'on', reverse && 'rev')}
      style={{ animationDuration: `${dashDuration(kw)}s` }}
      d={d}
    />
  );
}

/** Solar, home, grid and battery nodes with animated lines for the active power flows. */
export function FlowDiagram({ solarKw, loadKw, chargeKw, gridKw, exportKw, soc }: FlowValues) {
  const gridActive = gridKw > 0 || exportKw > 0;
  const gridValue =
    gridKw > 0 ? `${gridKw.toFixed(1)} kW` : exportKw > 0 ? `${exportKw.toFixed(1)} kW` : 'Idle';

  return (
    <svg
      viewBox="0 0 360 232"
      role="img"
      aria-label={`Energy flow. Solar produces ${solarKw.toFixed(1)} kilowatts. Home uses ${loadKw.toFixed(1)}. Battery charging ${chargeKw.toFixed(1)}. Grid ${gridKw > 0 ? 'importing ' + gridKw.toFixed(1) : 'idle'}.`}
    >
      <Flow d="M180 68 V118" on={solarKw > 0} kw={solarKw} />
      <Flow
        d="M82 150 H148"
        on={gridActive}
        reverse={exportKw > 0 && gridKw === 0}
        kw={gridKw || exportKw}
      />
      <Flow d="M212 150 H278" on={chargeKw > 0} kw={chargeKw} />
      <Node x={180} y={36} icon="sun" on={solarKw > 0} />
      <text className="nl" x="222" y="32">
        Solar
      </text>
      <text className="nv" x="222" y="50">
        {`${solarKw.toFixed(1)} kW`}
      </text>
      <Node x={180} y={150} icon="home" on />
      <text className="nl" x="180" y="202" textAnchor="middle">
        Home
      </text>
      <text className="nv" x="180" y="220" textAnchor="middle">
        {`${loadKw.toFixed(1)} kW`}
      </text>
      <Node x={50} y={150} icon="grid" on={gridActive} />
      <text className="nl" x="50" y="202" textAnchor="middle">
        {exportKw > 0 ? 'Exporting' : 'Grid'}
      </text>
      <text className="nv" x="50" y="220" textAnchor="middle">
        {gridValue}
      </text>
      <Node x={310} y={150} icon="battery" on={chargeKw > 0} />
      <text className="nl" x="310" y="202" textAnchor="middle">
        {`Battery ${soc}%`}
      </text>
      <text className="nv" x="310" y="220" textAnchor="middle">
        {chargeKw > 0 ? `+${chargeKw.toFixed(1)} kW` : '0 kW'}
      </text>
    </svg>
  );
}
