/** A house with rooftop panels, a battery and a flowing line between them. */
export function StepSiteIllustration() {
  return (
    <svg
      className="ill"
      viewBox="0 0 120 80"
      aria-hidden="true"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="98" cy="18" r="6.5" fill="var(--accent)" />
      <g className="spin" stroke="var(--accent)" strokeWidth="2">
        <path d="M98 6v3M98 27v3M86 18h3M107 18h3M89.5 9.5l2 2M104.5 24.5l2 2M89.5 26.5l2-2M104.5 11.5l2-2" />
      </g>
      <path d="M10 70h100" stroke="var(--line-strong)" strokeWidth="2" />
      <path d="M24 70V42L50 24l26 18v28z" fill="#fff" stroke="var(--primary)" strokeWidth="2" />
      <g transform="rotate(35 63 33)">
        <rect x="52" y="29" width="22" height="8" rx="1.5" fill="var(--primary)" stroke="none" />
        <path d="M59.3 29v8M66.7 29v8M52 33h22" stroke="#fff" strokeWidth=".8" opacity=".7" />
      </g>
      <rect
        x="37"
        y="54"
        width="9"
        height="16"
        rx="1.5"
        fill="var(--tint)"
        stroke="var(--primary)"
        strokeWidth="1.5"
      />
      <rect
        x="56"
        y="50"
        width="12"
        height="10"
        rx="1.5"
        fill="var(--tint)"
        stroke="var(--primary)"
        strokeWidth="1.5"
      />
      <path className="fl" d="M76 62h12" stroke="var(--primary)" strokeWidth="2" />
      <rect
        x="88"
        y="46"
        width="18"
        height="24"
        rx="3.5"
        fill="#fff"
        stroke="var(--primary)"
        strokeWidth="2"
      />
      <rect x="94" y="42" width="6" height="4" rx="1" fill="var(--primary)" stroke="none" />
      <rect
        className="blink b3"
        x="92"
        y="52"
        width="10"
        height="4"
        rx="1"
        fill="var(--primary)"
        stroke="none"
      />
      <rect
        className="blink b2"
        x="92"
        y="58"
        width="10"
        height="4"
        rx="1"
        fill="var(--primary)"
        stroke="none"
      />
      <rect
        className="blink b1"
        x="92"
        y="64"
        width="10"
        height="3"
        rx="1"
        fill="var(--primary)"
        stroke="none"
      />
    </svg>
  );
}
