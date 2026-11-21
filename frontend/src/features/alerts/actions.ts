'use server';

import { attempt, fail, ok, text, type ActionResult } from '@/services/http/action-result';
import { apiFetch } from '@/services/http/client';
import { usingMocks } from '@/services/mode';

export async function markAllAlertsReadAction(): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const result = await attempt(() => apiFetch<void>('/api/alerts/read-all', { method: 'POST' }));
  return result.ok ? ok() : result;
}

/** Marks one alert read (POST /api/alerts/{id}/read); its id is the server's, passed back unchanged. */
export async function markAlertReadAction(alertId: unknown): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const id = text(alertId, 64);
  if (!id) return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<void>(`/api/alerts/${encodeURIComponent(id)}/read`, { method: 'POST' }),
  );
  return result.ok ? ok() : result;
}
