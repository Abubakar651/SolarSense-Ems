/** Rounds and groups thousands, e.g. 12719.4 -> "12,719". */
export const fmt = (n: number): string => Math.round(n).toLocaleString('en-US');

/** Zero-pads to two digits: 7 -> "07". */
export const pad = (n: number): string => String(n).padStart(2, '0');
