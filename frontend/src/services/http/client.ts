import { redirect } from 'next/navigation';
import { headers } from 'next/headers';
import { readSessionToken } from './session';

const DEFAULT_BASE_URL = 'http://localhost:8000';
const TIMEOUT_MS = 10_000;

/**
 * A non-2xx answer from the API. `code` is the backend's machine-readable `detail`, e.g. "invalid_credentials";
 * `body` is the whole JSON answer, for the few errors that carry more than a code.
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly body: unknown = null,
  ) {
    super(`API ${status}: ${code}`);
    this.name = 'ApiError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  /** Send the session token (default). Public auth calls pass false. */
  auth?: boolean;
}

function baseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_BASE_URL).replace(/\/$/, '');
}

/** Fields whose validation errors get their own code, so the form can say what to fix. */
const FIELD_ERROR_CODES: Record<string, string> = { inverter_host: 'invalid_inverter_host' };

function validationCode(detail: unknown): string {
  const issues: unknown[] = Array.isArray(detail) ? detail : [];
  for (const issue of issues) {
    const loc = issue && typeof issue === 'object' ? (issue as { loc?: unknown }).loc : null;
    if (!Array.isArray(loc)) continue;
    for (const part of loc) {
      if (typeof part === 'string' && Object.hasOwn(FIELD_ERROR_CODES, part)) {
        return FIELD_ERROR_CODES[part] as string;
      }
    }
  }
  return 'validation_error';
}

/** FastAPI puts a string code in `detail` for our errors and a list of issues for validation (422). */
export function errorCode(status: number, payload: unknown): string {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const { detail } = payload as { detail: unknown };
    if (typeof detail === 'string') return detail;
    if (status === 422) return validationCode(detail);
  }
  return status >= 500 ? 'server_error' : `http_${status}`;
}

/**
 * Calls the SolarSense API from the Next.js server (server components and server actions only).
 * The browser's IP is forwarded so the API's per-client rate limits see real users, not this server.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = options;
  const outgoing = new Headers({ Accept: 'application/json' });
  if (body !== undefined) outgoing.set('Content-Type', 'application/json');
  const forwardedFor = (await headers()).get('x-forwarded-for');
  if (forwardedFor) outgoing.set('X-Forwarded-For', forwardedFor);
  if (auth) {
    const token = await readSessionToken();
    if (!token) throw new ApiError(401, 'not_authenticated');
    outgoing.set('Authorization', `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl()}${path}`, {
      method,
      headers: outgoing,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    throw new ApiError(503, 'api_unreachable');
  }

  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(response.status, errorCode(response.status, payload), payload);
  return payload as T;
}

/**
 * GET for server-component reads. A missing, expired or revoked session sends the user to log in
 * (keeping where they were going); other failures surface to the route's error boundary.
 */
export async function apiGet<T>(path: string, returnTo?: string): Promise<T> {
  return readOrLogin(() => apiFetch<T>(path), returnTo);
}

/** A read that the API takes as a POST (e.g. /api/v2/optimize); same session handling as apiGet. */
export async function apiPostRead<T>(path: string, body: unknown): Promise<T> {
  return readOrLogin(() => apiFetch<T>(path, { method: 'POST', body }));
}

async function readOrLogin<T>(call: () => Promise<T>, returnTo?: string): Promise<T> {
  try {
    return await call();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirect(returnTo ? `/login?next=${encodeURIComponent(returnTo)}` : '/login');
    }
    throw error;
  }
}
