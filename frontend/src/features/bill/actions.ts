'use server';

import { attempt, fail, ok, type ActionResult } from '@/services/http/action-result';
import { usingMocks } from '@/services/mode';
import {
  fetchBillEstimate,
  fetchProsumerComparison,
} from '@/services/repositories/bill/bill-tools.http';
import type {
  BillEstimate,
  BillEstimateRequest,
  ProsumerCompareRequest,
  ProsumerComparison,
} from '@/types/domain/tariff';

const isRequest = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

/** Works out a LESCO bill on the server. Null in the mock demo, which has no bill engine. */
export async function estimateBillAction(
  request: BillEstimateRequest,
): Promise<ActionResult<BillEstimate | null>> {
  if (usingMocks()) return ok(null);
  if (!isRequest(request)) return fail('validation_error');
  return attempt(() => fetchBillEstimate(request));
}

/** Settles the same month under net metering and net billing. Null in the mock demo. */
export async function compareProsumerAction(
  request: ProsumerCompareRequest,
): Promise<ActionResult<ProsumerComparison | null>> {
  if (usingMocks()) return ok(null);
  if (!isRequest(request)) return fail('validation_error');
  return attempt(() => fetchProsumerComparison(request));
}
