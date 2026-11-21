'use client';

import { useEffect, useRef, useState } from 'react';
import { Icon } from '@/components/ui/icon';
import { useToast } from '@/providers/toast-provider';

const SAVED_FLASH_MS = 1100;

interface SaveBarProps {
  /** True while there are unsaved edits. */
  dirty: boolean;
  /** Resolves true when the settings were stored; on false the bar stays open with the edits. */
  onSave: () => Promise<boolean>;
  onDiscard: () => void;
}

/** Sticky "Unsaved changes" bar. After saving it shows "Saved" briefly before it hides. */
export function SaveBar({ dirty, onSave, onDiscard }: SaveBarProps) {
  const toast = useToast();
  const [flash, setFlash] = useState(false);
  const [saving, setSaving] = useState(false);
  const timer = useRef(0);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const save = async () => {
    if (saving) return;
    setSaving(true);
    const stored = await onSave();
    setSaving(false);
    if (!stored) return;
    toast('Settings saved. Your next plan will use them.');
    setFlash(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setFlash(false), SAVED_FLASH_MS);
  };

  return (
    <div
      className="savebar"
      id="savebar"
      hidden={!dirty && !flash}
      role="region"
      aria-label="Unsaved changes"
    >
      <span>
        <b>Unsaved changes</b>{' '}
        <span className="xs" style={{ opacity: 0.8 }}>
          Settings apply to your next plan.
        </span>
      </span>
      <span className="row">
        <button className="btn btn-secondary btn-sm" type="button" id="discard" onClick={onDiscard}>
          Discard
        </button>
        <button
          className="btn btn-primary btn-sm"
          type="button"
          id="saveSet"
          style={{ background: '#fff', color: 'var(--text)' }}
          disabled={saving}
          onClick={() => void save()}
        >
          {flash ? (
            <>
              <Icon name="check" />
              Saved
            </>
          ) : (
            'Save changes'
          )}
        </button>
      </span>
    </div>
  );
}
