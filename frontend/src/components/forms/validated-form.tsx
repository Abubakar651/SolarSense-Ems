'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react';
import { validateValue, type Rule } from '@/lib/validators';
import { ErrorSummary, type FieldProblem } from './error-summary';

interface FieldRegistration {
  label: string;
  rules: Rule[];
  /** Fields of a multi-step form share a group; see `activeGroup`. */
  group?: string;
}

interface FormContextValue {
  errors: Record<string, string>;
  register: (id: string, registration: FieldRegistration) => void;
  /** Validates one field (used when it loses focus with a value). */
  check: (id: string) => void;
}

const FormContext = createContext<FormContextValue | null>(null);

export function useFormField() {
  const value = useContext(FormContext);
  if (!value) throw new Error('Field must be used inside <ValidatedForm>');
  return value;
}

interface ValidatedFormProps {
  children: ReactNode;
  /** Runs once every checked field is valid; receives the form so callers can read its values. */
  onValid: (form: HTMLFormElement) => void;
  /** Multi-step forms: only fields registered with this group are checked on submit. */
  activeGroup?: string;
  /** Clears the inputs after a valid submit (e.g. a change-password form). */
  resetOnValid?: boolean;
}

/**
 * Collects the rules of the fields rendered inside it, validates on blur (when a value is
 * present) and on submit, and shows an error summary that links to each problem.
 */
export function ValidatedForm({
  children,
  onValid,
  activeGroup,
  resetOnValid = false,
}: ValidatedFormProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const fields = useRef(new Map<string, FieldRegistration>());
  const summaryRef = useRef<HTMLDivElement>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [problems, setProblems] = useState<FieldProblem[]>([]);

  const register = useCallback((id: string, registration: FieldRegistration) => {
    fields.current.set(id, registration);
  }, []);

  const readValue = useCallback((id: string): string | boolean => {
    const element = formRef.current?.elements.namedItem(id);
    if (!(element instanceof HTMLInputElement)) return '';
    return element.type === 'checkbox' ? element.checked : element.value;
  }, []);

  const messageFor = useCallback(
    (id: string): string => {
      const field = fields.current.get(id);
      if (!field) return '';
      return validateValue(readValue(id), field.rules, {
        label: field.label,
        valueOf: (otherId) => String(readValue(otherId)),
      });
    },
    [readValue],
  );

  const check = useCallback(
    (id: string) => setErrors((current) => ({ ...current, [id]: messageFor(id) })),
    [messageFor],
  );

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const next: Record<string, string> = {};
    const found: FieldProblem[] = [];
    for (const [id, field] of fields.current) {
      if (activeGroup !== undefined && field.group !== activeGroup) continue;
      next[id] = messageFor(id);
      if (next[id]) found.push({ id, message: next[id] });
    }
    setErrors((current) => ({ ...current, ...next }));
    setProblems(found);
    if (found.length) return;
    onValid(form);
    if (resetOnValid) form.reset();
  };

  // The summary is revealed by the render that sets the problems; focus it once it is shown.
  useEffect(() => {
    if (problems.length) summaryRef.current?.focus();
  }, [problems]);

  return (
    <FormContext.Provider value={{ errors, register, check }}>
      <form ref={formRef} noValidate onSubmit={onSubmit}>
        <ErrorSummary ref={summaryRef} problems={problems} />
        {children}
      </form>
    </FormContext.Provider>
  );
}
