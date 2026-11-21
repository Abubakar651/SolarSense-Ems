import { cn } from '@/lib/cn';
import { MAX_KW_FOR_SPEED, dashDuration, flowDescription, type FlowValues } from './flow-diagram';

interface HouseFlowProps extends FlowValues {
  /** The grid is down: the grid wire is drawn cut and carries nothing. */
  gridDown?: boolean;
}

const PANEL_COLUMNS = [140, 159, 178, 197, 216, 235];
const PANEL_ROWS = [104, 126];
const BATTERY_INNER = { x: 304, bottom: 222, width: 22, height: 48 };

function Wire({
  d,
  kw,
  on,
  reverse = false,
}: {
  d: string;
  kw: number;
  on: boolean;
  reverse?: boolean;
}) {
  return (
    <path
      className={cn('ln', on && 'on', reverse && 'rev')}
      style={{ animationDuration: `${dashDuration(kw)}s` }}
      d={d}
    />
  );
}

function Label({ x, name, value }: { x: number; name: string; value: string }) {
  return (
    <>
      <text className="nl" x={x} y="246" textAnchor="middle">
        {name}
      </text>
      <text className="nv" x={x} y="262" textAnchor="middle">
        {value}
      </text>
    </>
  );
}

/** The site as a house: the panels glow with the sun, wires carry the flows and the battery fills with its charge. */
export function HouseFlow({ gridDown = false, ...values }: HouseFlowProps) {
  const { solarKw, loadKw, chargeKw, gridKw, exportKw, soc } = values;
  const sunStrength = Math.min(solarKw, MAX_KW_FOR_SPEED) / MAX_KW_FOR_SPEED;
  const batteryFill = (BATTERY_INNER.height * Math.min(Math.max(soc, 0), 100)) / 100;
  const exporting = !gridDown && exportKw > 0 && gridKw === 0;
  const gridName = gridDown ? 'Grid down' : exporting ? 'Exporting' : 'Grid';
  const gridValue = gridDown
    ? '0 kW'
    : gridKw > 0
      ? `${gridKw.toFixed(1)} kW`
      : exportKw > 0
        ? `${exportKw.toFixed(1)} kW`
        : 'Idle';

  return (
    <svg
      className="house-flow"
      viewBox="0 0 400 268"
      role="img"
      aria-label={flowDescription(values)}
    >
      <line className="hf-ground" x1="12" y1="226" x2="388" y2="226" />

      <g className={cn('hf-sun', solarKw > 0 && 'on')}>
        <circle cx="352" cy="44" r="14" />
        {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => (
          <line
            key={angle}
            x1="352"
            y1="24"
            x2="352"
            y2="18"
            transform={`rotate(${angle} 352 44)`}
          />
        ))}
      </g>

      <path
        className="hf-pylon"
        d="M36 226 L50 118 L64 226 M38 140 H62 M32 156 H68 M43 186 L57 166 M57 186 L43 166"
      />
      {gridDown ? (
        <path className="ln cut" d="M68 156 Q 92 178 110 178" />
      ) : (
        <Wire
          d="M68 156 Q 92 178 110 178"
          kw={gridKw || exportKw}
          on={gridKw > 0 || exportKw > 0}
          reverse={exporting}
        />
      )}

      <rect className="hf-wall" x="110" y="150" width="170" height="76" />
      <polygon className="hf-roof" points="96,152 294,152 262,96 128,96" />
      {PANEL_ROWS.flatMap((y) =>
        PANEL_COLUMNS.map((x) => (
          <rect key={`${x}-${y}`} className="hf-panel" x={x} y={y} width="17" height="18" />
        )),
      )}
      <rect
        className="hf-glow"
        x="140"
        y="104"
        width="112"
        height="40"
        style={{ opacity: sunStrength * 0.55 }}
      />
      <rect className="hf-door" x="130" y="186" width="24" height="40" />
      <rect className={cn('hf-win', loadKw > 0 && 'on')} x="172" y="168" width="30" height="24" />
      <rect className={cn('hf-win', loadKw > 0 && 'on')} x="214" y="168" width="30" height="24" />
      <rect className="hf-inv" x="254" y="166" width="18" height="24" />

      <Wire d="M246 144 V 158 H 263 V 166" kw={solarKw} on={solarKw > 0} />
      <Wire d="M272 182 H 300" kw={chargeKw} on={chargeKw > 0} />

      <rect className="hf-bat" x="300" y="170" width="30" height="56" />
      <rect
        className="hf-bat-fill"
        x={BATTERY_INNER.x}
        y={BATTERY_INNER.bottom - batteryFill}
        width={BATTERY_INNER.width}
        height={batteryFill}
      />

      <text className="nl" x="352" y="84" textAnchor="middle">
        Solar
      </text>
      <text className="nv" x="352" y="100" textAnchor="middle">
        {`${solarKw.toFixed(1)} kW`}
      </text>
      <Label x={50} name={gridName} value={gridValue} />
      <Label x={195} name="Home" value={`${loadKw.toFixed(1)} kW`} />
      <Label
        x={315}
        name={`Battery ${soc}%`}
        value={chargeKw > 0 ? `+${chargeKw.toFixed(1)} kW` : '0 kW'}
      />
    </svg>
  );
}
