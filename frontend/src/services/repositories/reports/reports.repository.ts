import type { ReportData } from '@/types/domain/reports';

export interface ReportsRepository {
  getReport(): Promise<ReportData>;
}
