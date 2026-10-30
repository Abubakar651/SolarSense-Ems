import { LOGO_MARK_MARKUP } from './logo-mark-markup';

/** SolarSense mark: a rising sun over a pulse line. Inherits the theme colour from `.mark`. */
export function LogoMark() {
  return (
    <svg
      className="mark"
      aria-hidden="true"
      viewBox="0 0 32 32"
      dangerouslySetInnerHTML={{ __html: LOGO_MARK_MARKUP }}
    />
  );
}
