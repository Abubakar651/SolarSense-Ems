'use client';

import type { ButtonHTMLAttributes } from 'react';
import { useToast } from '@/providers/toast-provider';

type ToastButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'onClick' | 'type'> & {
  message: string;
};

/** A button that only shows a toast: stands in for actions that are not built yet. */
export function ToastButton({ message, ...rest }: ToastButtonProps) {
  const toast = useToast();
  return <button type="button" onClick={() => toast(message)} {...rest} />;
}
