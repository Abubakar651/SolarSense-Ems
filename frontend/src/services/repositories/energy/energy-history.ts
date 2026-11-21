import type { DailyEnergyDay, EnergyHistory, MonthEnergy } from '@/types/domain/energy';
import type { EnergyHistoryDto } from '../../http/dto';
import { MONTHLY_METER } from '../../mock/lhr-res-01';
import { DAILY_ENERGY } from '../../mock/lhr-res-01-history';

/** The API's daily and monthly rows as screen records. Months reach back up to 24 where the API sends them. */
export function toEnergyHistory(dto: EnergyHistoryDto): EnergyHistory {
  const months = dto.monthly_history ?? dto.monthly;
  return {
    days: dto.daily.map((d): DailyEnergyDay => ({
      date: d.date,
      solarKwh: d.solar_kwh,
      loadKwh: d.load_kwh,
      importKwh: d.import_kwh,
      exportKwh: d.export_kwh,
      batteryChargedKwh: d.battery_charged_kwh ?? null,
      batteryDischargedKwh: d.battery_discharged_kwh ?? null,
    })),
    months: months.map((m): MonthEnergy => ({
      month: m.month,
      solarKwh: m.pv_kwh,
      loadKwh: m.load_kwh,
      importKwh: m.purchased_kwh,
      exportKwh: m.sold_kwh,
    })),
  };
}

/** The sample site's recorded rows; the sample data has no battery totals per day. */
export function sampleEnergyHistory(): EnergyHistory {
  return {
    days: DAILY_ENERGY.map(([date, solarKwh, loadKwh, importKwh, exportKwh]) => ({
      date,
      solarKwh,
      loadKwh,
      importKwh,
      exportKwh,
      batteryChargedKwh: null,
      batteryDischargedKwh: null,
    })),
    months: MONTHLY_METER.map((m) => ({
      month: m.month,
      solarKwh: m.pvKwh,
      loadKwh: m.loadKwh,
      importKwh: m.purchasedKwh,
      exportKwh: m.soldKwh,
    })),
  };
}
