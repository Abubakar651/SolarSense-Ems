import type { DayPlan, DayPlanResult } from '@/types/domain/energy';
import type { HistoryNotReady, HistoryResult } from '@/types/domain/history';

/** Unwraps a result that is always ready (sample data, or a test's known-ready mock); throws otherwise. */
export function readyData<T>(result: HistoryResult<T>): T {
  if (result.status !== 'ready') throw new Error(`Expected a ready result, got ${result.status}`);
  return result.data;
}

/** The plan equivalent of readyData, for the DayPlanResult union. */
export function readyPlan(result: DayPlanResult): DayPlan {
  if (result.status !== 'ready') throw new Error(`Expected a ready plan, got ${result.status}`);
  return result.plan;
}

/** The message a history screen shows while its data isn't ready yet. */
export function historyNotReadyLabel(
  result: HistoryNotReady,
  unavailableMessage = 'This history is not available for your site yet.',
): string {
  return result.status === 'collecting'
    ? `Collecting data · ${result.loggedDays} ${result.loggedDays === 1 ? 'day' : 'days'} logged`
    : unavailableMessage;
}
