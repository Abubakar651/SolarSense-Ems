import type { HistoryResult } from '@/types/domain/history';
import type { ReportData, ReportEmailPrefs } from '@/types/domain/reports';

export interface ReportsRepository {
  getReport(): Promise<HistoryResult<ReportData>>;
  getEmailPrefs(): Promise<ReportEmailPrefs>;
}
