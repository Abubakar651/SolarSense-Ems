import type { IconName } from '@/components/ui/icon-paths';
import { pad } from '@/lib/format';
import type { DayPlan } from '@/types/domain/energy';
import type { HistoryResult } from '@/types/domain/history';
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

function soilingItem(soiling: SoilingData): AttentionItem {
  const payback = paybackDays(soiling, soiling.defaultWashCostPkr);
  return {
    icon: 'sun',
    tone: isDusty(soiling) ? 'warn' : 'ok',
    title: isDusty(soiling) ? 'Panels are getting dusty' : 'Panels are clean',
    detail:
      `${lossPercent(soiling)}% output lost · ` +
      (payback === null ? 'no cost yet' : `wash pays back in ${payback} days`),
    link: { href: '/panels', label: 'See details' },
  };
}

function outageItem(outage: OutageData): AttentionItem {
  const busiestHour = outage.riskByHour.indexOf(Math.max(...outage.riskByHour));
  const lastOutage = outage.recent[0];
  return {
    icon: 'zap',
    tone: 'info',
    title: `Outages are most common around ${pad(busiestHour)}:00`,
    detail:
      `${outage.riskByHour[busiestHour]}% of days` +
      (lastOutage ? ` · last ${lastOutage.date}, ${lastOutage.duration}` : ''),
    link: { href: '/outage', label: 'See history' },
  };
}

/**
 * Up to three things the dashboard points out, each worked out from the backend-sourced data. The dust
 * and outage cards are left out while the site has no such history (or no outage) yet; the plan card always shows.
 */
export function attentionItems(
  plan: DayPlan,
  soiling: HistoryResult<SoilingData>,
  outage: HistoryResult<OutageData>,
): AttentionItem[] {
  const peakGridKwh = plan.grid
    .filter((_, hour) => hour >= plan.peakStartHour && hour < plan.peakEndHour)
    .reduce((a, b) => a + b, 0);

  return [
    ...(soiling.status === 'ready' ? [soilingItem(soiling.data)] : []),
    ...(outage.status === 'ready' && outage.data.totalCount > 0 ? [outageItem(outage.data)] : []),
    {
      icon: 'check',
      tone: 'ok',
      title: 'Plan ready for tonight',
      detail:
        peakGridKwh === 0
          ? 'Battery covers the whole peak'
          : `${peakGridKwh.toFixed(1)} kWh from the grid at peak`,
    },
  ];
}
