import type { CSSProperties, ReactNode } from 'react';

interface CardHeaderProps {
  title: string;
  subtitle?: string;
  /** Right-aligned badge or button. */
  action?: ReactNode;
  style?: CSSProperties;
}

export function CardHeader({ title, subtitle, action, style }: CardHeaderProps) {
  return (
    <div className="card-h" style={style}>
      {subtitle ? (
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      ) : (
        <h2>{title}</h2>
      )}
      {action}
    </div>
  );
}
