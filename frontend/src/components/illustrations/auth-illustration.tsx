const PANEL_X = [14, 76] as const;
const RAY_COUNT = 8;

/** One spoke per 22.5 degrees across the upper half of the sun (radius 74 to 92). */
function sunRays(): string {
  let path = '';
  for (let i = 0; i <= RAY_COUNT; i++) {
    const angle = (Math.PI * i) / RAY_COUNT;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    path += `M${(230 + 74 * cos).toFixed(1)} ${(170 - 74 * sin).toFixed(1)}`;
    path += `L${(230 + 92 * cos).toFixed(1)} ${(170 - 92 * sin).toFixed(1)}`;
  }
  return path;
}

const BATTERY_BARS = [
  { y: 128, className: 'blink b3' },
  { y: 142, className: 'blink b2' },
  { y: 156, className: 'blink b1' },
] as const;

/** Sunrise over panels and a battery, drawn in white on the brand panel. */
export function AuthIllustration() {
  return (
    <svg
      className="auth-ill"
      viewBox="0 0 460 220"
      aria-hidden="true"
      fill="none"
      stroke="#fff"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M0 170H460" strokeOpacity=".35" strokeWidth="2" />
      <path d="M170 170a60 60 0 0 1 120 0z" fill="rgba(255,255,255,.16)" stroke="none" />
      <path d="M188 170a42 42 0 0 1 84 0z" fill="rgba(255,255,255,.24)" stroke="none" />
      <path className="sunrays" d={sunRays()} strokeOpacity=".55" strokeWidth="2.5" />
      {PANEL_X.map((x) => (
        <g key={x} transform={`translate(${x} 128)`}>
          <path
            d="M0 22 10 0H50L40 22Z"
            fill="rgba(255,255,255,.12)"
            strokeOpacity=".6"
            strokeWidth="2"
          />
          <path d="M20 0 10 22M30 0 20 22M5 11H45" strokeOpacity=".35" strokeWidth="1.5" />
          <path d="M25 22V42" strokeOpacity=".5" strokeWidth="2" />
        </g>
      ))}
      <rect
        x="360"
        y="118"
        width="46"
        height="52"
        rx="8"
        fill="rgba(255,255,255,.12)"
        strokeOpacity=".6"
        strokeWidth="2"
      />
      <rect
        x="376"
        y="110"
        width="14"
        height="8"
        rx="2"
        fill="#fff"
        fillOpacity=".6"
        stroke="none"
      />
      {BATTERY_BARS.map(({ y, className }) => (
        <rect
          key={y}
          className={className}
          x="368"
          y={y}
          width="30"
          height="8"
          rx="2"
          fill="#fff"
          fillOpacity=".7"
          stroke="none"
        />
      ))}
      <path className="fl" d="M126 188H356" strokeOpacity=".6" strokeWidth="2" />
    </svg>
  );
}
