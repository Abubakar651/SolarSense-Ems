import Link from 'next/link';

export function LandingFooter() {
  return (
    <footer className="land-foot">
      <div className="wrap">
        <span>
          © 2026 SolarSense. Figures shown are recorded data from one home system in Lahore, not
          live.
        </span>
        <span className="row" style={{ gap: 16 }}>
          <Link href="/login">Log in</Link>
          <Link href="/signup">Create account</Link>
        </span>
      </div>
    </footer>
  );
}
