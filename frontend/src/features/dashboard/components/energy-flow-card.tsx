'use client';

import { useState } from 'react';
import { FlowDiagram } from '@/components/charts/flow-diagram';
import { HouseFlow } from '@/components/charts/house-flow';
import { CardHeader } from '@/components/ui/card-header';
import { Seg } from '@/components/ui/seg';
import type { DashboardSnapshot } from '../view-model';

const FLOW_VIEWS = [
  { value: 'house', label: 'House' },
  { value: 'diagram', label: 'Diagram' },
] as const;

/** Where the power is going now, drawn as a house or as a node diagram. */
export function EnergyFlowCard({ snap }: { snap: DashboardSnapshot }) {
  const [view, setView] = useState<'house' | 'diagram'>('house');

  return (
    <div className="card">
      <CardHeader
        title="Energy flow"
        subtitle={
          snap.source === 'offline'
            ? 'Inverter offline. Showing the planned flow for this hour'
            : 'Where your power is going right now'
        }
        action={
          <div className="row">
            <Seg
              options={FLOW_VIEWS}
              value={view}
              onChange={setView}
              ariaLabel="Energy flow view"
            />
            <span className={`badge b-${snap.grid.tone}`}>
              {snap.grid.tone === 'ok' && <span className="dot live" />}
              {snap.grid.label}
            </span>
          </div>
        }
      />
      <div className="flow" id="flow">
        {view === 'house' ? (
          <HouseFlow {...snap} gridDown={snap.grid.tone === 'bad'} />
        ) : (
          <FlowDiagram {...snap} />
        )}
      </div>
      <p className="sr-only" id="flow-sum">
        {snap.flowSummary}
      </p>
    </div>
  );
}
