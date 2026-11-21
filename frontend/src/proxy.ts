import { NextResponse, type NextRequest } from 'next/server';
import { SESSION_COOKIE } from '@/services/http/session-cookie';

/**
 * Optimistic gate: app screens without a session cookie go to /login?next=… before any rendering.
 * It only checks that a cookie exists. The API validates the token on every call, and an expired
 * or revoked one sends the user back to /login from the page itself.
 */
export function proxy(request: NextRequest) {
  if (process.env.NEXT_PUBLIC_USE_MOCKS !== 'false') return NextResponse.next();
  if (request.cookies.get(SESSION_COOKIE)?.value) return NextResponse.next();

  const login = new URL('/login', request.url);
  login.searchParams.set('next', `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/plan/:path*',
    '/energy/:path*',
    '/savings/:path*',
    '/bill/:path*',
    '/inverter/:path*',
    '/outage/:path*',
    '/panels/:path*',
    '/alerts/:path*',
    '/reports/:path*',
    '/settings/:path*',
    '/onboarding/:path*',
  ],
};
