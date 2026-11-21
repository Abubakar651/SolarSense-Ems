import type { SoilingResult } from '@/types/domain/panels';

export interface PanelsRepository {
  getSoiling(): Promise<SoilingResult>;
}
