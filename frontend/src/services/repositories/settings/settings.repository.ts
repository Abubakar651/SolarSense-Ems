import type { SettingsData } from '@/types/domain/settings';

export interface SettingsRepository {
  getSettings(): Promise<SettingsData>;
}
