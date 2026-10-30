import { alertsMock } from './repositories/alerts/alerts.mock';
import type { AlertsRepository } from './repositories/alerts/alerts.repository';
import { energyMock } from './repositories/energy/energy.mock';
import type { EnergyRepository } from './repositories/energy/energy.repository';
import { outageMock } from './repositories/outage/outage.mock';
import type { OutageRepository } from './repositories/outage/outage.repository';
import { panelsMock } from './repositories/panels/panels.mock';
import type { PanelsRepository } from './repositories/panels/panels.repository';
import { reportsMock } from './repositories/reports/reports.mock';
import type { ReportsRepository } from './repositories/reports/reports.repository';
import { savingsMock } from './repositories/savings/savings.mock';
import type { SavingsRepository } from './repositories/savings/savings.repository';
import { settingsMock } from './repositories/settings/settings.mock';
import type { SettingsRepository } from './repositories/settings/settings.repository';

export interface Services {
  energy: EnergyRepository;
  alerts: AlertsRepository;
  savings: SavingsRepository;
  outage: OutageRepository;
  panels: PanelsRepository;
  reports: ReportsRepository;
  settings: SettingsRepository;
}

/**
 * Every repository is mocked for now. To wire a screen to the backend, add an `*.http.ts`
 * implementation next to its repository interface and return it here (see README).
 */
export function getServices(): Services {
  return {
    energy: energyMock,
    alerts: alertsMock,
    savings: savingsMock,
    outage: outageMock,
    panels: panelsMock,
    reports: reportsMock,
    settings: settingsMock,
  };
}
