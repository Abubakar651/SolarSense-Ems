import { Brand } from '@/components/brand/brand';

/** Floating brand link shown on the auth and onboarding screens. */
export function AuthBar({ layout }: { layout: 'auth' | 'onboard' }) {
  return (
    <div className="authbar" data-layout={layout}>
      <Brand href="/" hideWordmarkOnXs style={{ color: 'var(--text)' }} />
    </div>
  );
}
