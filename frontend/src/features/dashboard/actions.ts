'use server';

import { getServices } from '@/services';
import type { InverterReading } from '@/types/domain/inverter';

/** Polled by the dashboard so the "now" tiles follow the inverter. An unreachable inverter comes back as offline. */
export async function readInverterAction(): Promise<InverterReading> {
  return getServices().inverter.getLive();
}
