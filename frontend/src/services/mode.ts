/**
 * True while every screen is served from the typed mocks. Anything other than
 * NEXT_PUBLIC_USE_MOCKS=false keeps mocks on, so tests, e2e and design parity never need a backend.
 */
export function usingMocks(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCKS !== 'false';
}
