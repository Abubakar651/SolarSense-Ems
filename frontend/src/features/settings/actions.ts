'use server';

import { revalidatePath } from 'next/cache';
import { attempt, fail, ok, text, type ActionResult } from '@/services/http/action-result';
import { apiFetch } from '@/services/http/client';
import type { SettingsDto, TokenDto } from '@/services/http/dto';
import { clearSession, writeSession } from '@/services/http/session';
import { usingMocks } from '@/services/mode';
import type { SettingsUpdate } from './view-model';

/** Saves every tab at once. The API validates the body; this only forwards it. */
export async function saveSettingsAction(update: SettingsUpdate): Promise<ActionResult> {
  if (usingMocks()) return ok();
  if (!update || typeof update !== 'object') return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<SettingsDto>('/api/settings', { method: 'PUT', body: update }),
  );
  if (!result.ok) return result;
  revalidatePath('/', 'layout');
  return ok();
}

/**
 * Changing the password signs out every other session. The API returns a fresh token for this
 * one, which replaces the cookie so the user stays logged in here.
 */
export async function changePasswordAction(input: {
  current: unknown;
  next: unknown;
}): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const current = text(input.current);
  const next = text(input.next);
  if (!current || !next) return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<TokenDto>('/api/auth/change-password', {
      method: 'POST',
      body: { current_password: current, new_password: next },
    }),
  );
  if (!result.ok) return result;
  await writeSession(result.data.access_token, result.data.expires_in, false);
  return ok();
}

/** Permanently deletes the account (the API cascades every row it owns) and ends the session. */
export async function deleteAccountAction(password: unknown): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const value = text(password);
  if (!value) return fail('invalid_password');
  const result = await attempt(() =>
    apiFetch<void>('/api/me', { method: 'DELETE', body: { confirm: 'DELETE', password: value } }),
  );
  if (!result.ok) return result;
  await clearSession();
  return ok();
}
