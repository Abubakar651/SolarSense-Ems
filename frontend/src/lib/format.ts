/** Rounds and groups thousands, e.g. 12719.4 -> "12,719". */
export const fmt = (n: number): string => Math.round(n).toLocaleString('en-US');

/** Zero-pads to two digits: 7 -> "07". */
export const pad = (n: number): string => String(n).padStart(2, '0');

/** "Zaeem Ahmed" -> "ZA"; one letter for a single name, "?" when there is none. */
export function initials(name: string): string {
  const letters = name
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]!.toUpperCase());
  return letters.join('') || '?';
}
