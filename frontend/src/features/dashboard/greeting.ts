const MORNING_FROM_HOUR = 5;
const AFTERNOON_FROM_HOUR = 12;
const EVENING_FROM_HOUR = 17;

/** "Good morning" from 05:00, "Good afternoon" from 12:00, "Good evening" from 17:00 (local hour). */
export function greetingForHour(hour: number): string {
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    throw new RangeError(`Hour must be 0 to 23, got ${hour}`);
  }
  if (hour < MORNING_FROM_HOUR || hour >= EVENING_FROM_HOUR) return 'Good evening';
  if (hour < AFTERNOON_FROM_HOUR) return 'Good morning';
  return 'Good afternoon';
}

/** The name as the greeting uses it: "Zaeem Ahmed" -> "Zaeem". */
export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? name;
}

/** The hour of the day in the station's timezone, whatever the server's clock is set to. */
export function hourInKarachi(now: Date): number {
  // h23 (not hour12:false) keeps midnight as "0", not "24".
  const formatted = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Karachi',
    hour: 'numeric',
    hourCycle: 'h23',
  }).format(now);
  return Number(formatted);
}
