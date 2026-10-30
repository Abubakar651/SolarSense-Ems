export interface ChoiceOption<T extends string> {
  value: T;
  title: string;
  description: string;
  badge?: { text: string; tone: 'ok' | 'neutral' | 'primary' };
  disabled?: boolean;
}

interface ChoiceGroupProps<T extends string> {
  name: string;
  ariaLabel: string;
  options: ReadonlyArray<ChoiceOption<T>>;
  value: T;
  onChange: (value: T) => void;
}

/** Radio group drawn as selectable cards. */
export function ChoiceGroup<T extends string>({
  name,
  ariaLabel,
  options,
  value,
  onChange,
}: ChoiceGroupProps<T>) {
  return (
    <div className="choice" role="radiogroup" aria-label={ariaLabel}>
      {options.map((option) => (
        <label key={option.value}>
          <input
            type="radio"
            name={name}
            value={option.value}
            checked={option.value === value}
            disabled={option.disabled}
            onChange={() => onChange(option.value)}
          />
          <span>
            <b>
              {option.badge ? `${option.title} ` : option.title}
              {option.badge && (
                <span className={`badge b-${option.badge.tone}`} style={{ marginLeft: 6 }}>
                  {option.badge.text}
                </span>
              )}
            </b>
            <span className="small muted">{option.description}</span>
          </span>
        </label>
      ))}
    </div>
  );
}
