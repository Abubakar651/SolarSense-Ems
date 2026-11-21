'use client';

import { useState } from 'react';
import { CardHeader } from '@/components/ui/card-header';
import { fmt } from '@/lib/format';
import type { SoilingData } from '@/types/domain/panels';
import { parseCost, washAdvice } from '../view-model';

/** "Should you wash them?": compares the cost of dust over the look-ahead window with the cleaning cost. */
export function WashCalculator({ soiling }: { soiling: SoilingData }) {
  const [input, setInput] = useState(String(soiling.defaultWashCostPkr));
  const cost = parseCost(input);
  const advice = washAdvice(soiling, cost);

  return (
    <div className="card">
      <CardHeader
        title="Should you wash them?"
        subtitle={
          advice.rainSoon
            ? `Rain is forecast in ${advice.days} days`
            : advice.rainUnknown
              ? `No rain forecast · assumes ${advice.days} dry days`
              : undefined
        }
      />
      <div className="field">
        <label htmlFor="wash-cost">Cost of one cleaning (PKR)</label>
        <input
          className="input num"
          id="wash-cost"
          inputMode="numeric"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          aria-describedby="wash-h"
        />
        <p className="hint" id="wash-h">
          Labour and water
        </p>
      </div>
      <div id="wash-result" aria-live="polite">
        <div className="plan-card" style={{ padding: 'var(--sp-4)', background: 'var(--subtle)' }}>
          <div className="small muted">
            {advice.rainSoon
              ? `Dust cost until the rain, in ${advice.days} days`
              : `Dust cost over the next ${advice.days} days`}
          </div>
          <b className="num" style={{ fontSize: '1.125rem' }}>
            {advice.formula}
          </b>
        </div>
        {advice.wash ? (
          <div className="note wash" style={{ margin: 'var(--sp-3) 0 0' }}>
            <b>Wash them.</b>
            {' Saves '}
            <b>{`PKR ${fmt(advice.netPkr)}`}</b>
            {' net.'}
          </div>
        ) : (
          <div className="note wait" style={{ margin: 'var(--sp-3) 0 0' }}>
            <b>Wait.</b>
            {` Washing costs PKR ${fmt(-advice.netPkr)} more than the dust${advice.rainSoon ? ' before the rain' : ''}.`}
          </div>
        )}
      </div>
    </div>
  );
}
