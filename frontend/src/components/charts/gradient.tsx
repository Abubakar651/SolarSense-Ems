/** Vertical fade from 30% to 2% of `color`: the soft area fill under a line. */
export function FadeGradient({ id, color = 'var(--primary)' }: { id: string; color?: string }) {
  return (
    <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" style={{ stopColor: color, stopOpacity: 0.3 }} />
      <stop offset="1" style={{ stopColor: color, stopOpacity: 0.02 }} />
    </linearGradient>
  );
}
