'use client';

import { useCountUp } from '@/hooks/use-count-up';

/** A number that counts up from zero the first time it appears. */
export function CountUp({ value }: { value: string }) {
  return <span>{useCountUp(value)}</span>;
}
