import { cache } from 'react';
import type { PeakWindow } from '@/lib/tariff';
import { apiGet } from '../../http/client';
import type { TariffRepository } from './tariff.repository';

/** GET /api/v2/tariff/peak-window?month=N (PeakWindowResponse in src/api/schemas.py). */
export interface PeakWindowDto {
  month: number;
  season: string;
  peak_start_hour: number;
  peak_end_hour: number;
}

const MONTHS = 12;
const monthIndex = (month: number) => month % MONTHS;

/**
 * One response per month -> the four season rows the Settings screen lists. Months are rotated so a
 * season that crosses New Year keeps its display order (Winter comes out as 12, 1, 2, not 1, 2, 12).
 */
export function toPeakWindows(dtos: readonly PeakWindowDto[]): PeakWindow[] {
  if (dtos.length !== MONTHS) {
    throw new Error(`Expected ${MONTHS} peak-window months, got ${dtos.length}`);
  }

  const bySeason = new Map<string, PeakWindowDto[]>();
  for (const dto of dtos) {
    const months = bySeason.get(dto.season) ?? [];
    months.push(dto);
    bySeason.set(dto.season, months);
  }

  const windows = [...bySeason.entries()].map(([season, months]) => {
    const present = new Set(months.map((dto) => dto.month));
    // The season starts at the month whose predecessor is not in the season.
    const first = months.find((dto) => !present.has(((dto.month + MONTHS - 2) % MONTHS) + 1));
    if (!first) throw new Error(`Season ${season} has no start month`);
    const ordered = Array.from(
      { length: months.length },
      (_, i) => ((first.month - 1 + i) % MONTHS) + 1,
    );
    return {
      season: season as PeakWindow['season'],
      months: ordered,
      startHour: first.peak_start_hour,
      endHour: first.peak_end_hour,
    };
  });

  // Jan is month 1 but the winter row leads the table, so order by the season's first month mod 12.
  return windows.sort(
    (a, b) => monthIndex(a.months[0] as number) - monthIndex(b.months[0] as number),
  );
}

const fetchPeakWindows = cache(async (): Promise<PeakWindow[]> => {
  const responses = await Promise.all(
    Array.from({ length: MONTHS }, (_, i) =>
      apiGet<PeakWindowDto>(`/api/v2/tariff/peak-window?month=${i + 1}`, '/settings'),
    ),
  );
  return toPeakWindows(responses);
});

export const tariffHttp: TariffRepository = { getPeakWindows: fetchPeakWindows };
