'use client';

import { useState, type CSSProperties } from 'react';
import { CardHeader } from '@/components/ui/card-header';
import { Icon } from '@/components/ui/icon';
import { monthLabel, shortDate } from '@/lib/dates';
import type { DailyEnergyDay } from '@/types/domain/energy';
import { intensity, monthsCovered, monthWeeks } from '../calendar';

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
/** The faintest day still shows a little colour. */
const MIN_HEAT_PCT = 20;

/** A month of daily solar generation, each day shaded from the month's lowest to its highest. */
export function SolarCalendar({ days }: { days: DailyEnergyDay[] }) {
  const months = monthsCovered(days);
  const [index, setIndex] = useState(months.length - 1);
  const month = months[index] as string;
  const weeks = monthWeeks(month, days);
  const values = weeks.flat().flatMap((day) => (day?.solarKwh == null ? [] : [day.solarKwh]));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const total = values.reduce((a, b) => a + b, 0);

  return (
    <div className="card">
      <CardHeader
        title="Daily solar"
        subtitle={`${total.toFixed(0)} kWh in ${monthLabel(month)}`}
        action={
          <div className="row">
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setIndex(index - 1)}
              disabled={index === 0}
              aria-label="Previous month"
            >
              <Icon name="arrow" style={{ transform: 'rotate(180deg)' }} />
            </button>
            <b aria-live="polite">{monthLabel(month)}</b>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setIndex(index + 1)}
              disabled={index === months.length - 1}
              aria-label="Next month"
            >
              <Icon name="arrow" />
            </button>
          </div>
        }
      />
      <table className="cal">
        <caption className="sr-only">{`Solar generated each day in ${monthLabel(month)}, in kWh`}</caption>
        <thead>
          <tr>
            {WEEKDAYS.map((weekday) => (
              <th key={weekday} scope="col">
                {weekday}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {weeks.map((week) => (
            <tr key={week.find((day) => day !== null)?.date}>
              {week.map((day, slot) => {
                if (day === null) return <td key={slot} className="empty" />;
                if (day.solarKwh === null) {
                  return (
                    <td
                      key={day.date}
                      className="nodata"
                      aria-label={`${shortDate(day.date)}: no data`}
                    >
                      <span className="d">{day.day}</span>
                    </td>
                  );
                }
                const heat =
                  MIN_HEAT_PCT + (100 - MIN_HEAT_PCT) * intensity(day.solarKwh, min, max);
                return (
                  <td key={day.date}>
                    <span className="d">{day.day}</span>
                    <span className="v num">{day.solarKwh.toFixed(1)}</span>
                    <span
                      className="heat"
                      aria-hidden="true"
                      style={{ '--heat': `${heat.toFixed(0)}%` } as CSSProperties}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="cal-legend" aria-hidden="true">
        <span className="num">{`${min.toFixed(1)} kWh`}</span>
        <i />
        <span className="num">{`${max.toFixed(1)} kWh`}</span>
      </div>
    </div>
  );
}
