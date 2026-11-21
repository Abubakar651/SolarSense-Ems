import { accountHttp } from './repositories/account/account.http';
import { accountMock } from './repositories/account/account.mock';
import type { AccountRepository } from './repositories/account/account.repository';
import { advisoryHttp } from './repositories/advisory/advisory.http';
import { advisoryMock } from './repositories/advisory/advisory.mock';
import type { AdvisoryRepository } from './repositories/advisory/advisory.repository';
import { alertsHttp } from './repositories/alerts/alerts.http';
import { alertsMock } from './repositories/alerts/alerts.mock';
import type { AlertsRepository } from './repositories/alerts/alerts.repository';
import { billHttp } from './repositories/bill/bill.http';
import { billMock } from './repositories/bill/bill.mock';
import type { BillRepository } from './repositories/bill/bill.repository';
import { energyHttp } from './repositories/energy/energy.http';
import { energyMock } from './repositories/energy/energy.mock';
import type { EnergyRepository } from './repositories/energy/energy.repository';
import { inverterHttp } from './repositories/inverter/inverter.http';
import { inverterMock } from './repositories/inverter/inverter.mock';
import type { InverterRepository } from './repositories/inverter/inverter.repository';
import { outageHttp } from './repositories/outage/outage.http';
import { outageMock } from './repositories/outage/outage.mock';
import type { OutageRepository } from './repositories/outage/outage.repository';
import { panelsHttp } from './repositories/panels/panels.http';
import { panelsMock } from './repositories/panels/panels.mock';
import type { PanelsRepository } from './repositories/panels/panels.repository';
import { reportsHttp } from './repositories/reports/reports.http';
import { reportsMock } from './repositories/reports/reports.mock';
import type { ReportsRepository } from './repositories/reports/reports.repository';
import { savingsHttp } from './repositories/savings/savings.http';
import { savingsMock } from './repositories/savings/savings.mock';
import type { SavingsRepository } from './repositories/savings/savings.repository';
import { settingsHttp } from './repositories/settings/settings.http';
import { settingsMock } from './repositories/settings/settings.mock';
import type { SettingsRepository } from './repositories/settings/settings.repository';
import { tariffHttp } from './repositories/tariff/tariff.http';
import { tariffMock } from './repositories/tariff/tariff.mock';
import type { TariffRepository } from './repositories/tariff/tariff.repository';
import { usingMocks } from './mode';

export interface Services {
  account: AccountRepository;
  energy: EnergyRepository;
  alerts: AlertsRepository;
  savings: SavingsRepository;
  outage: OutageRepository;
  panels: PanelsRepository;
  reports: ReportsRepository;
  settings: SettingsRepository;
  inverter: InverterRepository;
  bill: BillRepository;
  advisory: AdvisoryRepository;
  tariff: TariffRepository;
}

/**
 * With NEXT_PUBLIC_USE_MOCKS=false every repository reads the API; with mocks on, the sample data.
 * To add a screen, put an `*.http.ts` next to its repository interface and return it here (see README).
 */
export function getServices(): Services {
  return buildServices(usingMocks());
}

/** The sample site's data, for public pages (the landing page) that must never need a login. */
export function getSampleServices(): Services {
  return buildServices(true);
}

function buildServices(mocks: boolean): Services {
  return {
    account: mocks ? accountMock : accountHttp,
    energy: mocks ? energyMock : energyHttp,
    alerts: mocks ? alertsMock : alertsHttp,
    savings: mocks ? savingsMock : savingsHttp,
    outage: mocks ? outageMock : outageHttp,
    panels: mocks ? panelsMock : panelsHttp,
    reports: mocks ? reportsMock : reportsHttp,
    settings: mocks ? settingsMock : settingsHttp,
    inverter: mocks ? inverterMock : inverterHttp,
    bill: mocks ? billMock : billHttp,
    advisory: mocks ? advisoryMock : advisoryHttp,
    tariff: mocks ? tariffMock : tariffHttp,
  };
}
