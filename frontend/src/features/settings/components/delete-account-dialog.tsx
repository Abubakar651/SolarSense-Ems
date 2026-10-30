'use client';

import { useState } from 'react';
import { Dialog } from '@/components/ui/dialog';

const CONFIRM_WORD = 'DELETE';

interface DeleteAccountDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
}

/** Destructive confirmation: the delete button stays disabled until the user types DELETE. */
export function DeleteAccountDialog({ open, onClose, onConfirm }: DeleteAccountDialogProps) {
  return (
    <Dialog open={open} onClose={onClose} labelledBy="delT">
      {/* Mounted only while open, so the typed text resets every time. */}
      {open && <ConfirmForm onCancel={onClose} onConfirm={onConfirm} />}
    </Dialog>
  );
}

function ConfirmForm({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: () => void }) {
  const [typed, setTyped] = useState('');

  return (
    <>
      <h2 id="delT" style={{ color: 'var(--bad)' }}>
        Delete your account?
      </h2>
      <p className="muted" style={{ margin: '8px 0 var(--sp-4)' }}>
        This permanently deletes your account, site settings and history. Type <b>{CONFIRM_WORD}</b>{' '}
        to confirm.
      </p>
      <div className="field">
        <label htmlFor="delIn">Confirmation</label>
        <input
          className="input"
          id="delIn"
          autoComplete="off"
          value={typed}
          onChange={(event) => setTyped(event.target.value)}
        />
      </div>
      <div className="row" style={{ justifyContent: 'flex-end' }}>
        <button className="btn btn-secondary" type="button" id="delCancel" onClick={onCancel}>
          Cancel
        </button>
        <button
          className="btn btn-danger"
          type="button"
          id="delGo"
          disabled={typed !== CONFIRM_WORD}
          onClick={onConfirm}
        >
          Delete account
        </button>
      </div>
    </>
  );
}
