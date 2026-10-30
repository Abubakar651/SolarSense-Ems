import Link from 'next/link';
import { PublicShell } from '@/components/layout/public-shell';
import { ErrorState } from '@/components/ui/error-state';

export default function NotFound() {
  return (
    <PublicShell layout="landing">
      <ErrorState
        title="Page not found"
        message="The page you are looking for does not exist or has moved."
        action={
          <Link className="btn btn-primary" href="/">
            Back to home
          </Link>
        }
      />
    </PublicShell>
  );
}
