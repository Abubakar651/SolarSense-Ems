import { Icon } from '@/components/ui/icon';

/** Inline error under a field; stays in the DOM (hidden) so aria-describedby always resolves. */
export function FieldError({ id, message }: { id: string; message: string }) {
  return (
    <p className="err" id={id} hidden={!message}>
      {message && (
        <>
          <Icon name="alert" style={{ width: 16, height: 16, marginTop: 1 }} />
          <span>{message}</span>
        </>
      )}
    </p>
  );
}
