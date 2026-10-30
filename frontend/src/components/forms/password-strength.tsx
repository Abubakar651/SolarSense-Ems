/** Four-segment meter under the sign-up password (0 = empty, 4 = strongest). */
export function PasswordStrength({ score }: { score: 0 | 1 | 2 | 3 | 4 }) {
  return (
    <div
      className="strength"
      data-s={score}
      aria-hidden="true"
      style={{ margin: '-8px 0 var(--sp-4)' }}
    >
      <i />
      <i />
      <i />
      <i />
    </div>
  );
}
