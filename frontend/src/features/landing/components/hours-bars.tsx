import type { DayPlan } from '@/types/domain/energy';

/** Usage by hour; the evening peak hours use the solid brand colour. */
export function HoursBars({ plan }: { plan: DayPlan }) {
  const top = Math.max(...plan.load);
  return (
    <div
      className="hours"
      role="img"
      aria-label="Bar chart of hourly usage. Evening hours from 18:00 to 22:00 are the highest and are highlighted as peak."
    >
      {plan.load.map((kw, hour) => (
        <i
          key={hour}
          className={hour >= plan.peakStartHour && hour < plan.peakEndHour ? 'pk' : ''}
          style={{ height: `${Math.round((kw / top) * 100)}%` }}
        />
      ))}
    </div>
  );
}
