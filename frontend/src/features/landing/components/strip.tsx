import { Icon } from '@/components/ui/icon';
import { COMPATIBILITY } from '../content';

export function Strip() {
  return (
    <section className="strip" aria-label="Compatibility">
      <div className="wrap">
        <span className="t">Built around</span>
        <ul>
          {COMPATIBILITY.map(({ icon, label }) => (
            <li key={label}>
              <Icon name={icon} />
              {label}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
