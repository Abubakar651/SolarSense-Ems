/** A sun with a tick: the "all caught up" empty state. */
export function EmptyIllustration() {
  return (
    <svg
      className="ill-empty"
      viewBox="0 0 96 72"
      aria-hidden="true"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="48" cy="36" r="21" fill="var(--tint)" />
      <g className="spin" stroke="var(--accent)" strokeWidth="2.5">
        <path d="M48 4v5M48 63v5M16 36h5M75 36h5M25.4 13.4l3.5 3.5M67.1 55.1l3.5 3.5M25.4 58.6l3.5-3.5M67.1 16.9l3.5-3.5" />
      </g>
      <path d="M38 37l7 7 13-14" stroke="var(--primary)" strokeWidth="3.5" />
    </svg>
  );
}
