import type { InverterReading } from '@/types/domain/inverter';

export interface InverterRepository {
  /** The inverter's current readings, or an offline result when it cannot be reached. */
  getLive(): Promise<InverterReading>;
}
