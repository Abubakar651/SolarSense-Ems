const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-10-26" -> "Oct 26". */
export function shortDate(iso: string): string {
  return `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${Number(iso.slice(8, 10))}`;
}

/** 206 -> "3 h 26 m"; 55 -> "55 m". */
export function durationLabel(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (hours === 0) return `${rest} m`;
  return `${hours} h ${String(rest).padStart(2, '0')} m`;
}

/** "2026-10-07" -> "Oct 7, 2026". */
export function longDate(iso: string): string {
  return `${shortDate(iso)}, ${iso.slice(0, 4)}`;
}
