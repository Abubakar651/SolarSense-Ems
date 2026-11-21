'use client';

import { useState } from 'react';
import { useToast } from '@/providers/toast-provider';
import { recordPanelWashAction } from '../actions';

/**
 * "I washed the panels today": records the wash so the dust estimate restarts from today. Disabled once
 * today's wash is recorded.
 */
export function WashButton({ washedToday }: { washedToday: boolean }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);

  const record = async () => {
    if (saving) return;
    setSaving(true);
    const result = await recordPanelWashAction();
    setSaving(false);
    toast(result.ok ? 'Wash recorded. The dust estimate restarts from today.' : result.error);
  };

  return (
    <button
      className="btn btn-secondary btn-sm"
      type="button"
      disabled={saving || washedToday}
      onClick={() => void record()}
    >
      {washedToday ? 'Washed today' : 'I washed the panels today'}
    </button>
  );
}
