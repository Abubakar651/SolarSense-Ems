import type { Ref } from 'react';

export interface FieldProblem {
  id: string;
  message: string;
}

interface ErrorSummaryProps {
  problems: FieldProblem[];
  ref?: Ref<HTMLDivElement>;
}

/** Lists every failed field after a submit; each message links to its input. */
export function ErrorSummary({ problems, ref }: ErrorSummaryProps) {
  const count = problems.length;

  return (
    <div className="errsum" role="alert" tabIndex={-1} hidden={!count} ref={ref}>
      {count > 0 && (
        <>
          <b>{`Please fix ${count} ${count > 1 ? 'problems' : 'problem'}:`}</b>
          <ul>
            {problems.map(({ id, message }) => (
              <li key={id}>
                <a
                  href={`#${id}`}
                  onClick={(event) => {
                    event.preventDefault();
                    document.getElementById(id)?.focus();
                  }}
                >
                  {message}
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
