import { cookies } from 'next/headers';
import { PENDING_EMAIL_COOKIE, SESSION_COOKIE } from './session-cookie';

// The session cookie holds the API's JWT and is httpOnly: browser JS can't read it, only this
// server sends it on to the API.

const PENDING_EMAIL_MAX_AGE = 24 * 60 * 60;

function baseCookie() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
  };
}

export async function readSessionToken(): Promise<string | undefined> {
  return (await cookies()).get(SESSION_COOKIE)?.value;
}

/** "Keep me logged in" makes the cookie outlive the browser session; otherwise it ends with it. */
export async function writeSession(token: string, expiresInSeconds: number, remember: boolean) {
  (await cookies()).set(SESSION_COOKIE, token, {
    ...baseCookie(),
    ...(remember ? { maxAge: expiresInSeconds } : {}),
  });
}

export async function clearSession() {
  (await cookies()).delete(SESSION_COOKIE);
}

export async function writePendingEmail(email: string) {
  (await cookies()).set(PENDING_EMAIL_COOKIE, email, {
    ...baseCookie(),
    maxAge: PENDING_EMAIL_MAX_AGE,
  });
}

export async function readPendingEmail(): Promise<string | undefined> {
  return (await cookies()).get(PENDING_EMAIL_COOKIE)?.value;
}

export async function clearPendingEmail() {
  (await cookies()).delete(PENDING_EMAIL_COOKIE);
}
