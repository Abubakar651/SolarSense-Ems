'use client';

interface SegProps<T extends string> {
  options: ReadonlyArray<{ value: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
  id?: string;
}

/** Segmented single-choice control (e.g. 7 days / 30 days / 12 months). */
export function Seg<T extends string>({ options, value, onChange, ariaLabel, id }: SegProps<T>) {
  return (
    <div className="seg" role="group" aria-label={ariaLabel} id={id}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
