import Link from 'next/link';
import { Icon } from '@/components/ui/icon';

const RIPPLE_RADII = [90, 160, 230, 300] as const;

/** Closing call to action on the one solid brand-colour panel of the page. */
export function CtaBand() {
  return (
    <section className="cta-band" aria-label="Get started">
      <div className="wrap">
        <div className="cta-panel">
          <svg className="cta-ill" viewBox="0 0 900 300" aria-hidden="true">
            {RIPPLE_RADII.map((r) => (
              <circle key={r} cx="450" cy="300" r={r} />
            ))}
          </svg>
          <h2>See your first plan today</h2>
          <p>Create an account, connect your inverter and start saving at peak hours.</p>
          <div className="row" style={{ justifyContent: 'center' }}>
            <Link className="btn btn-primary btn-lg" href="/signup">
              Create your account
              <Icon name="arrow" className="btn-arrow" />
            </Link>
            <Link className="btn btn-secondary btn-lg" href="/login">
              Log in
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
