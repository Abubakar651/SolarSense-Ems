export type Point = readonly [x: number, y: number];

/**
 * SVG path through the points using a monotone cubic (Fritsch-Carlson) curve:
 * smooth, and it never overshoots the data between samples.
 */
export function smooth(points: readonly Point[]): string {
  const n = points.length;
  const first = points[0];
  if (!first) return '';
  const line = (p: Point, i: number) => `${i ? 'L' : 'M'}${p[0]},${p[1]}`;
  if (n < 3) return points.map(line).join(' ');

  const dx: number[] = [];
  const slope: number[] = [];
  const tangent: number[] = [];
  for (let i = 0; i < n - 1; i++) {
    const a = points[i] as Point;
    const b = points[i + 1] as Point;
    dx[i] = b[0] - a[0];
    slope[i] = (b[1] - a[1]) / (dx[i] as number);
  }
  tangent[0] = slope[0] as number;
  tangent[n - 1] = slope[n - 2] as number;
  for (let i = 1; i < n - 1; i++) {
    const prev = slope[i - 1] as number;
    const next = slope[i] as number;
    tangent[i] = prev * next <= 0 ? 0 : (prev + next) / 2;
  }
  for (let i = 0; i < n - 1; i++) {
    const m = slope[i] as number;
    if (m === 0) {
      tangent[i] = 0;
      tangent[i + 1] = 0;
      continue;
    }
    const a = (tangent[i] as number) / m;
    const b = (tangent[i + 1] as number) / m;
    const q = a * a + b * b;
    if (q > 9) {
      const k = 3 / Math.sqrt(q);
      tangent[i] = k * a * m;
      tangent[i + 1] = k * b * m;
    }
  }

  let d = `M${first[0]},${first[1]}`;
  for (let i = 0; i < n - 1; i++) {
    const a = points[i] as Point;
    const b = points[i + 1] as Point;
    const w = dx[i] as number;
    d += ` C${a[0] + w / 3},${a[1] + ((tangent[i] as number) * w) / 3}`;
    d += ` ${b[0] - w / 3},${b[1] - ((tangent[i + 1] as number) * w) / 3} ${b[0]},${b[1]}`;
  }
  return d;
}

/** Closed area under a smoothed line, down to the baseline `baseY`. */
export function smoothArea(points: readonly Point[], baseY: number): string {
  const first = points[0];
  const last = points[points.length - 1];
  if (!first || !last) return '';
  return `${smooth(points)} L${last[0]},${baseY} L${first[0]},${baseY}Z`;
}
