import type { SoilingData } from '@/types/domain/panels';

export interface PanelsRepository {
  getSoiling(): Promise<SoilingData>;
}
