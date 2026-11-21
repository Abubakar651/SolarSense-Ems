import { apiErrorMessage } from '@/lib/api-errors';
import { ApiError } from './client';

/** What a server action hands back to the form that called it. */
export type ActionResult<T = undefined> =
  { ok: true; data: T } | { ok: false; error: string; code: string };

export function ok(): ActionResult;
export function ok<T>(data: T): ActionResult<T>;
export function ok<T>(data?: T): ActionResult<T | undefined> {
  return { ok: true, data };
}

export function fail(code: string): { ok: false; error: string; code: string } {
  return { ok: false, error: apiErrorMessage(code), code };
}

/** Runs an API call and turns an ApiError into a failed result; anything else is a bug and rethrows. */
export async function attempt<T>(call: () => Promise<T>): Promise<ActionResult<T>> {
  try {
    return ok(await call());
  } catch (error) {
    if (error instanceof ApiError) return fail(error.code);
    throw error;
  }
}

/** Server-action arguments come from the browser: anything that isn't a bounded string is rejected. */
export function text(value: unknown, maxLength = 200): string | null {
  return typeof value === 'string' && value.length <= maxLength ? value : null;
}

/** Only same-site paths, so `?next=` can't send someone to another domain after login. */
export function safeNextPath(value: unknown): string | null {
  if (
    typeof value !== 'string' ||
    !value.startsWith('/') ||
    value.startsWith('//') ||
    value.includes('\\')
  ) {
    return null;
  }
  return value;
}
