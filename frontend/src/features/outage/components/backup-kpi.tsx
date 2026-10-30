'use client';

import { CountUp } from '@/components/ui/count-up';
import { KpiCard } from '@/components/ui/kpi-card';
import { backupHours } from '@/lib/backup-hours';
import { useSampleClock } from '@/providers/sample-clock-provider';
import type { DayPlan } from '@/types/domain/energy';

/** Hours the battery could carry the home right now (follows the sample clock). */
export function BackupKpi({ plan }: { plan: DayPlan }) {
  const { hour } = useSampleClock();

  return (
    <KpiCard
      label="Backup time now"
      value={
        <>
          <CountUp value={backupHours(plan, hour)} />
          <small>hours</small>
        </>
      }
      sub="At your current usage"
    />
  );
}
