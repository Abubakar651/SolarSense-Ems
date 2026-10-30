const MARGIN = { l: 34, r: 8, t: 10, b: 22 } as const;
const GAP = 34;
const SOLAR_MAX_KW = 6;

/** Geometry of the 24-hour plan chart: solar/usage area on top, battery strip below. */
export function planLayout(w: number, h: number) {
  const m = MARGIN;
  const iw = w - m.l - m.r;
  const batteryHeight = Math.max(54, h * 0.2);
  const solarHeight = h - m.t - m.b - batteryHeight - GAP;
  const solarBottom = m.t + solarHeight;
  const batteryTop = solarBottom + GAP;
  const batteryBottom = batteryTop + batteryHeight;

  return {
    m,
    iw,
    batteryTop,
    batteryBottom,
    /** Centre of an hourly slot. */
    x: (hour: number) => m.l + (iw * (hour + 0.5)) / 24,
    /** Left edge of a whole hour (used for the peak band). */
    hourEdge: (hour: number) => m.l + (iw * hour) / 24,
    ySolar: (kw: number) => solarBottom - (solarHeight * kw) / SOLAR_MAX_KW,
    yBattery: (pct: number) => batteryBottom - (batteryHeight * pct) / 100,
    /** Position of the "Now" marker for a clock time. */
    nowX: (hour: number, minute: number) => m.l + (iw * (hour + minute / 60)) / 24,
    tickEvery: w < 460 ? 6 : 3,
  };
}

export type PlanLayout = ReturnType<typeof planLayout>;
