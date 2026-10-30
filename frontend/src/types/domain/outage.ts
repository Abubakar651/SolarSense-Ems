export interface OutageEvent {
  date: string;
  started: string;
  duration: string;
  batteryUsed: string;
  /** True when the battery ran down to the outage reserve. */
  hitReserve: boolean;
}

export interface OutageData {
  /** Percent of recorded days on which a grid outage was in progress during each hour of the day. */
  riskByHour: number[];
  /** Newest first. */
  recent: OutageEvent[];
  /** First day of the recorded history, e.g. "Nov 20 2025". */
  since: string;
  /** Outages in the recorded history. */
  totalCount: number;
  thisMonth: { count: number; hours: number; hitReserve: number };
}
