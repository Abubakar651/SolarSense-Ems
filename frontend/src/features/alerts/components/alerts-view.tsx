'use client';

import { useState } from 'react';
import { EmptyIllustration } from '@/components/illustrations/empty-illustration';
import { Icon } from '@/components/ui/icon';
import { IconChip } from '@/components/ui/icon-chip';
import { PageHeader } from '@/components/ui/page-header';
import { useAlerts } from '@/providers/alerts-provider';
import { useToast } from '@/providers/toast-provider';
import { FILTERS, SEVERITY, countFor, filterAlerts, type AlertFilter } from '../view-model';

export function AlertsView() {
  const { alerts, markAllRead } = useAlerts();
  const toast = useToast();
  const [filter, setFilter] = useState<AlertFilter>('all');
  const rows = filterAlerts(alerts, filter);

  return (
    <section data-route="alerts">
      <PageHeader
        title="Alerts"
        actions={
          <button
            className="btn btn-secondary btn-sm"
            id="markRead"
            type="button"
            onClick={() => {
              markAllRead();
              toast('All alerts marked as read');
            }}
          >
            <Icon name="check" />
            Mark all as read
          </button>
        }
      >
        Things that need your attention, newest first.
      </PageHeader>
      <div className="card">
        <div
          className="chips"
          role="group"
          aria-label="Filter alerts"
          id="alertFilter"
          style={{ marginBottom: 'var(--sp-3)' }}
        >
          {FILTERS.map(({ value, label }) => (
            <button
              key={value}
              className="chip"
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {`${label} (${countFor(alerts, value)})`}
            </button>
          ))}
        </div>
        <ul className="list" id="alertList">
          {rows.map(({ id, severity, title, detail, when, unread }) => (
            <li key={id}>
              <IconChip icon={SEVERITY[severity].icon} tone={severity} />
              <div style={{ flex: 1 }}>
                <div className="row" style={{ gap: 8 }}>
                  <b>{title}</b>
                  {unread && <span className="badge b-primary">New</span>}
                  <span className="sr-only">{SEVERITY[severity].label}</span>
                </div>
                <p className="small muted">{detail}</p>
              </div>
              <span className="xs faint" style={{ whiteSpace: 'nowrap' }}>
                {when}
              </span>
            </li>
          ))}
        </ul>
        <div className="empty" id="alertEmpty" hidden={rows.length > 0}>
          <EmptyIllustration />
          <b>You&apos;re all caught up</b>
          <p className="small">No alerts match this filter.</p>
        </div>
      </div>
    </section>
  );
}
