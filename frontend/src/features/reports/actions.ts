'use server';

import { attempt, fail, ok, text, type ActionResult } from '@/services/http/action-result';
import { apiFetch } from '@/services/http/client';
import type { ReportPrefsDto } from '@/services/http/dto';
import { usingMocks } from '@/services/mode';
import type { ReportEmailPrefs } from '@/types/domain/reports';

export async function saveReportPrefsAction(prefs: ReportEmailPrefs): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const sendTo = text(prefs?.sendTo, 254);
  if (!sendTo || typeof prefs.monthly !== 'boolean' || typeof prefs.weekly !== 'boolean') {
    return fail('validation_error');
  }
  const result = await attempt(() =>
    apiFetch<ReportPrefsDto>('/api/report-preferences', {
      method: 'PUT',
      body: { monthly: prefs.monthly, weekly: prefs.weekly, send_to: sendTo },
    }),
  );
  return result.ok ? ok() : result;
}
