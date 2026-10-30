/** Rising savings bars with a rupee coin. */
export function StepSavingsIllustration() {
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
      <rect x="18" y="56" width="13" height="14" rx="3" fill="var(--tint-3)" />
      <rect x="36" y="46" width="13" height="24" rx="3" fill="var(--tint-3)" />
      <rect x="54" y="36" width="13" height="34" rx="3" fill="var(--tint-3)" />
      <rect x="72" y="24" width="13" height="46" rx="3" fill="var(--primary)" />
      <path
        d="M20 50l18-9 18-8 22-14"
        stroke="var(--primary)"
        strokeWidth="2"
        strokeDasharray="3 4"
        className="fl"
      />
      <g className="bob">
        <circle cx="98" cy="20" r="11" fill="var(--accent)" />
        <circle cx="98" cy="20" r="7.5" stroke="#fff" strokeWidth="1.5" opacity=".7" />
        <text
          x="98"
          y="24"
          textAnchor="middle"
          fontSize="10"
          fontWeight="700"
          fill="#fff"
          stroke="none"
          style={{ fontFamily: 'var(--font)' }}
        >
          Rs
        </text>
      </g>
    </svg>
  );
}
