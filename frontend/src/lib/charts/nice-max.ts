/** Rounds an axis maximum up to a 1/2/2.5/5/10 step so ticks land on friendly numbers. */
export function niceMax(value: number, steps = 4): { step: number; max: number } {
  const raw = value / steps;
  const power = 10 ** Math.floor(Math.log10(raw));
  const n = raw / power;
  const factor = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
  return { step: factor * power, max: factor * power * steps };
}
