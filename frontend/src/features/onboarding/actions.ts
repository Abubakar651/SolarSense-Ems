'use server';

import { attempt, fail, ok, type ActionResult } from '@/services/http/action-result';
import { apiFetch } from '@/services/http/client';
import type { SettingsDto } from '@/services/http/dto';
import { usingMocks } from '@/services/mode';
import type { OnboardingRequest } from './view-model';

/** Creates the user's site. A site that already exists counts as done, so a double submit is harmless. */
export async function completeOnboardingAction(request: OnboardingRequest): Promise<ActionResult> {
  if (usingMocks()) return ok();
  if (!request || typeof request !== 'object') return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<SettingsDto>('/api/site', { method: 'POST', body: request }),
  );
  if (!result.ok && result.code !== 'site_exists') return result;
  return ok();
}
