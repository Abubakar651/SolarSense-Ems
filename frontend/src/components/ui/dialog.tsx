'use client';

import { useEffect, useRef, type ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  /** Called when the dialog closes, including via Escape. */
  onClose: () => void;
  /** id of the heading that names the dialog. */
  labelledBy: string;
  children: ReactNode;
}

/** Modal built on the native <dialog>: focus is trapped, Escape closes it, focus returns after. */
export function Dialog({ open, onClose, labelledBy, children }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog ref={ref} aria-labelledby={labelledBy} onClose={onClose}>
      <div className="d-in">{children}</div>
    </dialog>
  );
}
