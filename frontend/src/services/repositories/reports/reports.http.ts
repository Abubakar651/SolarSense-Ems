import { apiGet } from '../../http/client';
import type { ReportPrefsDto } from '../../http/dto';
import { energyResult, fetchEnergyHistory, toEnergyRates } from '../insights.http';
import { settingsHttp } from '../settings/settings.http';
import { buildReport } from './reports.mock';
import type { ReportsRepository } from './reports.repository';

export const reportsHttp: ReportsRepository = {
  async getReport() {
    const [history, settings] = await Promise.all([
      fetchEnergyHistory(),
      settingsHttp.getSettings(),
    ]);
    return energyResult(history, (daily, meters, meteredThrough) => ({
      ...buildReport(
        `${settings.site.name} · ${settings.site.city}`,
        meters,
        daily,
        meteredThrough,
        toEnergyRates(history),
      ),
      hourlyThrough: history.hourly_through ?? null,
    }));
  },
  async getEmailPrefs() {
    const prefs = await apiGet<ReportPrefsDto>('/api/report-preferences', '/reports');
    return { monthly: prefs.monthly, weekly: prefs.weekly, sendTo: prefs.send_to };
  },
};
