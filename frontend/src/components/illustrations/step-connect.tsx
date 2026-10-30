/** Panels, an inverter with a signal, and a battery joined by flowing lines. */
export function StepConnectIllustration() {
  return (
    <svg
      className="ill"
      viewBox="0 0 120 80"
      aria-hidden="true"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M10 70h100" stroke="var(--line-strong)" strokeWidth="2" />
      <rect
        x="6"
        y="40"
        width="18"
        height="16"
        rx="2"
        fill="var(--tint)"
        stroke="var(--primary)"
        strokeWidth="2"
      />
      <path d="M12 40v16M18 40v16M6 48h18" stroke="var(--primary)" strokeWidth="1" opacity=".5" />
      <path className="fl" d="M24 48h18" stroke="var(--primary)" strokeWidth="2" />
      <path className="fl" d="M78 48h20" stroke="var(--primary)" strokeWidth="2" />
      <rect
        x="42"
        y="34"
        width="36"
        height="28"
        rx="6"
        fill="#fff"
        stroke="var(--primary)"
        strokeWidth="2"
      />
      <path d="M50 44h20M50 50h11" stroke="var(--tint-3)" strokeWidth="2" />
      <circle className="blink b1" cx="70" cy="54" r="2.5" fill="var(--primary)" stroke="none" />
      <circle cx="60" cy="27" r="2" fill="var(--primary)" stroke="none" />
      <path
        className="blink b1"
        d="M55.5 23.5a6.4 6.4 0 0 1 9 0"
        stroke="var(--primary)"
        strokeWidth="2"
      />
      <path
        className="blink b2"
        d="M51.5 19.5a12 12 0 0 1 17 0"
        stroke="var(--primary)"
        strokeWidth="2"
      />
      <path
        className="blink b3"
        d="M47.5 15.5a17.7 17.7 0 0 1 25 0"
        stroke="var(--primary)"
        strokeWidth="2"
      />
      <rect
        x="98"
        y="38"
        width="16"
        height="20"
        rx="3.5"
        fill="#fff"
        stroke="var(--primary)"
        strokeWidth="2"
      />
      <rect x="103" y="35" width="6" height="3" rx="1" fill="var(--primary)" stroke="none" />
      <path d="M102 46h8M102 51h8" stroke="var(--tint-3)" strokeWidth="2" />
    </svg>
  );
}
