import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  /** The line under the title. */
  children?: ReactNode;
  /** Controls aligned to the right of the title (range switch, buttons). */
  actions?: ReactNode;
}

export function PageHeader({ title, children, actions }: PageHeaderProps) {
  const heading = (
    <>
      <h1 tabIndex={-1}>{title}</h1>
      {children && <p>{children}</p>}
    </>
  );

  if (!actions) return <div className="page-h">{heading}</div>;
  return (
    <div className="page-h row between">
      <div>{heading}</div>
      {actions}
    </div>
  );
}
