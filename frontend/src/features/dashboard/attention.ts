import type { IconName } from '@/components/ui/icon-paths';
import { fmt, pad } from '@/lib/format';
import type { DayPlan } from '@/types/domain/energy';
import type { OutageData } from '@/types/domain/outage';
import type { SoilingData } from '@/types/domain/panels';
import { isDusty, lossPercent, paybackDays } from '../panels/view-model';

export interface AttentionItem {
  icon: IconName;
  tone: 'warn' | 'info' | 'ok';
  title: string;
  detail: string;
  link?: { href: string; label: string };
}

/** The three things the dashboard points out, each worked out from the backend-sourced data. */
export function attentionItems(
  plan: DayPlan,
  soiling: SoilingData,
  outage: OutageData,
): AttentionItem[] {
  const busiestHour = outage.riskByHour.indexOf(Math.max(...outage.riskByHour));
  const lastOutage = outage.recent[0];
  const peakGridKwh = plan.grid
    .filter((_, hour) => hour >= plan.peakStartHour && hour < plan.peakEndHour)
    .reduce((a, b) => a + b, 0);

  return [
    {
      icon: 'sun',
      tone: isDusty(soiling) ? 'warn' : 'ok',
      title: isDusty(soiling) ? 'Panels are getting dusty' : 'Panels are clean',
      detail:
        `The model estimates ${lossPercent(soiling)}% output lost since the ${soiling.lastWashed} wash. ` +
        `A cleaning at PKR ${fmt(soiling.defaultWashCostPkr)} pays back in about ${paybackDays(soiling, soiling.defaultWashCostPkr)} days.`,
      link: { href: '/panels', label: 'See details' },
    },
    {
      icon: 'zap',
      tone: 'info',
      title: `Outages are most common around ${pad(busiestHour)}:00`,
      detail:
        `${outage.riskByHour[busiestHour]}% of days had an outage in that hour.` +
        (lastOutage
          ? ` Last outage: ${lastOutage.date}, ${lastOutage.started} (${lastOutage.duration}).`
          : ''),
      link: { href: '/outage', label: 'See history' },
    },
    {
      icon: 'check',
      tone: 'ok',
      title: 'Plan ready for tonight',
      detail:
        peakGridKwh === 0
          ? 'The battery covers the whole evening peak, so no grid power is used then.'
          : `The battery covers most of the evening peak; ${peakGridKwh.toFixed(1)} kWh comes from the grid.`,
    },
  ];
}
