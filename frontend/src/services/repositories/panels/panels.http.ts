import type { DustCollecting } from '@/types/domain/panels';
import { ApiError } from '../../http/client';
import type { SoilingCollectingDto } from '../../http/dto';
import { fetchRainForecast, fetchSoilingHistory, toSoilingInput } from '../insights.http';
import { buildSoiling, type RainOutlook } from './panels.mock';
import type { PanelsRepository } from './panels.repository';

/** The rain forecast, or "unavailable" when the API could not fetch it; the screen still works without it. */
async function rainOutlook(): Promise<RainOutlook> {
  try {
    const forecast = await fetchRainForecast();
    return { available: true, daysUntilRain: forecast.days_until_rain };
  } catch (error) {
    if (error instanceof ApiError && error.code === 'rain_forecast_unavailable') {
      return { available: false, daysUntilRain: null };
    }
    throw error;
  }
}

function toCollecting(dto: SoilingCollectingDto): DustCollecting {
  return {
    status: 'collecting',
    loggedDays: dto.logged_days_since_clean,
    daysNeeded: dto.days_needed,
    clean:
      dto.clean_event && dto.clean_date ? { event: dto.clean_event, date: dto.clean_date } : null,
  };
}

/**
 * The site's dust model, from the API, laid out by the same builder as the sample data: fitted to the
 * site's own inverter log ("logged"), or the station's recorded model ("recorded").
 */
export const panelsHttp: PanelsRepository = {
  async getSoiling() {
    try {
      const [soiling, rain] = await Promise.all([fetchSoilingHistory(), rainOutlook()]);
      return {
        status: 'ready',
        data: buildSoiling(toSoilingInput(soiling), rain),
        freshness: {
          through: soiling.as_of,
          kind: soiling.source === 'live' ? 'logged' : 'recorded',
        },
      };
    } catch (error) {
      if (!(error instanceof ApiError)) throw error;
      if (error.status === 404 && error.code === 'soiling_collecting') {
        return toCollecting(error.body as SoilingCollectingDto);
      }
      // The model needs the day's sunlight; without it the screen shows the rest of the page.
      if (error.status === 503 && error.code === 'weather_unavailable')
        return { status: 'unavailable' };
      throw error;
    }
  },
};
