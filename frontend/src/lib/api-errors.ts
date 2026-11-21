/** User-facing copy for the API's error codes. Unknown codes fall back to a generic message. */
const MESSAGES: Record<string, string> = {
  invalid_credentials: 'That email and password don’t match. Check them and try again.',
  email_not_verified: 'Confirm your email first. We can send the link again from the verify page.',
  email_taken: 'An account with this email already exists. Log in instead.',
  invalid_token: 'This link has expired or was already used. Request a new one.',
  invalid_current_password: 'Your current password is not correct.',
  invalid_password: 'That password is not correct.',
  rate_limited: 'Too many attempts. Wait a few minutes and try again.',
  not_authenticated: 'Your session has ended. Please log in again.',
  site_exists: 'Your site is already set up.',
  site_not_found: 'Finish setting up your site first.',
  invalid_inverter_host:
    'Enter the inverter’s IP address on your home network, such as 192.168.1.50.',
  validation_error: 'Some details aren’t valid. Check the form and try again.',
  vision_unavailable: 'Photo analysis isn’t available right now. Try again later.',
  api_unreachable: 'We couldn’t reach SolarSense. Check your connection and try again.',
  server_error: 'Something went wrong on our side. Please try again.',
};

const FALLBACK = 'Something went wrong. Please try again.';

export function apiErrorMessage(code: string): string {
  return MESSAGES[code] ?? FALLBACK;
}
