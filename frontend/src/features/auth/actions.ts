'use server';

import { redirect } from 'next/navigation';
import {
  attempt,
  fail,
  ok,
  safeNextPath,
  text,
  type ActionResult,
} from '@/services/http/action-result';
import { apiFetch } from '@/services/http/client';
import type { TokenDto, UserDto } from '@/services/http/dto';
import {
  clearPendingEmail,
  clearSession,
  readPendingEmail,
  writePendingEmail,
  writeSession,
} from '@/services/http/session';
import { usingMocks } from '@/services/mode';

const DEFAULT_LANDING = '/dashboard';

interface LoginInput {
  email: unknown;
  password: unknown;
  remember: unknown;
  next: unknown;
}

/** Logs in and stores the token in the session cookie. Returns where to go next. */
export async function loginAction(
  input: LoginInput,
): Promise<ActionResult<{ redirectTo: string }>> {
  const next = safeNextPath(input.next) ?? DEFAULT_LANDING;
  if (usingMocks()) return ok({ redirectTo: next });

  const email = text(input.email, 254);
  const password = text(input.password, 200);
  if (!email || !password) return fail('validation_error');
  const remember = input.remember === true;

  const result = await attempt(() =>
    apiFetch<TokenDto>('/api/auth/login', {
      method: 'POST',
      auth: false,
      body: { email, password, remember },
    }),
  );
  if (!result.ok) return result;
  await writeSession(result.data.access_token, result.data.expires_in, remember);
  await clearPendingEmail();
  return ok({ redirectTo: result.data.user.onboarded ? next : '/onboarding' });
}

/**
 * Creates the account, then tries to log straight in. That succeeds only when the API doesn't require
 * email verification (REQUIRE_EMAIL_VERIFICATION=false); otherwise the user is sent to /verify.
 */
export async function signupAction(input: {
  name: unknown;
  email: unknown;
  password: unknown;
}): Promise<ActionResult<{ redirectTo: string }>> {
  if (usingMocks()) return ok({ redirectTo: '/verify' });
  const name = text(input.name, 100);
  const email = text(input.email, 254);
  const password = text(input.password, 200);
  if (!name || !email || !password) return fail('validation_error');

  const result = await attempt(() =>
    apiFetch<UserDto>('/api/auth/signup', {
      method: 'POST',
      auth: false,
      body: { name, email, password },
    }),
  );
  if (!result.ok) return result;

  const login = await attempt(() =>
    apiFetch<TokenDto>('/api/auth/login', {
      method: 'POST',
      auth: false,
      body: { email, password, remember: false },
    }),
  );
  if (login.ok) {
    await writeSession(login.data.access_token, login.data.expires_in, false);
    return ok({ redirectTo: '/onboarding' });
  }
  await writePendingEmail(result.data.email);
  return ok({ redirectTo: '/verify' });
}

export async function verifyEmailAction(token: unknown): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const value = text(token, 128);
  if (!value) return fail('invalid_token');
  const result = await attempt(() =>
    apiFetch<void>('/api/auth/verify-email', {
      method: 'POST',
      auth: false,
      body: { token: value },
    }),
  );
  return result.ok ? ok() : result;
}

/** Resends the link to the email remembered at signup. */
export async function resendVerificationAction(): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const email = await readPendingEmail();
  if (!email) return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<void>('/api/auth/verify-email/resend', {
      method: 'POST',
      auth: false,
      body: { email },
    }),
  );
  return result.ok ? ok() : result;
}

export async function forgotPasswordAction(email: unknown): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const value = text(email, 254);
  if (!value) return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<void>('/api/auth/forgot-password', {
      method: 'POST',
      auth: false,
      body: { email: value },
    }),
  );
  return result.ok ? ok() : result;
}

export async function resetPasswordAction(input: {
  token: unknown;
  password: unknown;
}): Promise<ActionResult> {
  if (usingMocks()) return ok();
  const token = text(input.token, 128);
  const password = text(input.password, 200);
  if (!token) return fail('invalid_token');
  if (!password) return fail('validation_error');
  const result = await attempt(() =>
    apiFetch<void>('/api/auth/reset-password', {
      method: 'POST',
      auth: false,
      body: { token, new_password: password },
    }),
  );
  if (!result.ok) return result;
  await clearSession();
  return ok();
}

/** Forgets the session on this device and returns to the login page. */
export async function logoutAction(): Promise<void> {
  if (!usingMocks()) await clearSession();
  redirect('/login');
}
