import type { ReactNode } from 'react';
import { Brand } from '@/components/brand/brand';
import { AuthIllustration } from '@/components/illustrations/auth-illustration';
import { Icon } from '@/components/ui/icon';

interface AuthLayoutProps {
  /** Identifies the screen (kept as data-route so route-level styles still apply). */
  route: string;
  heading: string;
  bullets?: string[];
  stat?: { value: string; label: string };
  /** The form card contents. */
  children: ReactNode;
}

/** Split auth screen: brand panel on the left (from 960px), form card on the right. */
export function AuthLayout({ route, heading, bullets, stat, children }: AuthLayoutProps) {
  return (
    <section className="auth-wrap" data-route={route}>
      <div className="auth-brand">
        <Brand href="/" />
        <h2>{heading}</h2>
        {bullets && (
          <ul>
            {bullets.map((bullet) => (
              <li key={bullet}>
                <Icon name="check" />
                {bullet}
              </li>
            ))}
          </ul>
        )}
        {stat && (
          <div className="stat">
            <b className="num">{stat.value}</b>
            <span>{stat.label}</span>
          </div>
        )}
        <AuthIllustration />
      </div>
      <div className="auth-form">
        <div className="auth-card">{children}</div>
      </div>
    </section>
  );
}
