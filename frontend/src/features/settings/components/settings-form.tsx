'use client';

import { createContext, useContext, type ReactNode } from 'react';
import type { SettingsValue, SettingsValues } from '../view-model';

interface SettingsFormContextValue {
  values: SettingsValues;
  set: (key: string, value: SettingsValue) => void;
}

const SettingsFormContext = createContext<SettingsFormContextValue | null>(null);

export function SettingsFormProvider({
  value,
  children,
}: {
  value: SettingsFormContextValue;
  children: ReactNode;
}) {
  return <SettingsFormContext.Provider value={value}>{children}</SettingsFormContext.Provider>;
}

function useSettingsForm(): SettingsFormContextValue {
  const value = useContext(SettingsFormContext);
  if (!value) throw new Error('Settings fields must be used inside <SettingsFormProvider>');
  return value;
}

/** A text setting and its setter. */
export function useTextSetting(key: string): [string, (value: string) => void] {
  const { values, set } = useSettingsForm();
  return [String(values[key] ?? ''), (value) => set(key, value)];
}

/** An on/off setting and its setter. */
export function useFlagSetting(key: string): [boolean, (value: boolean) => void] {
  const { values, set } = useSettingsForm();
  return [values[key] === true, (value) => set(key, value)];
}
