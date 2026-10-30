'use client';

import { useEffect, useRef, type ElementType, type ReactNode } from 'react';
import { useReducedMotion } from '@/hooks/use-reduced-motion';
import { whenInView } from '@/lib/in-view';

const STAGGER_MS = 60;
const SETTLE_MS = 1000;

interface RevealProps {
  as?: ElementType;
  className?: string;
  /** Position among siblings: delays the fade by `index * 60ms`. */
  index?: number;
  children: ReactNode;
}

/**
 * Fades its content up once as it scrolls into view. The element renders visible (so it works
 * without JS); once hydrated it is armed and revealed on entry. Skipped for reduced motion.
 *
 * The classes are toggled on the DOM node directly: React never re-renders this static wrapper,
 * and going through state would flash the content on every hydration.
 */
export function Reveal({ as: Tag = 'div', className, index = 0, children }: RevealProps) {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    const element = ref.current;
    if (!element || reduced) return;
    element.style.setProperty('--d', `${index * STAGGER_MS}ms`);
    element.classList.add('rv');
    let settle = 0;
    const cancel = whenInView(element, () => {
      element.classList.add('in');
      settle = window.setTimeout(() => {
        element.classList.remove('rv', 'in');
        element.style.removeProperty('--d');
      }, SETTLE_MS);
    });
    return () => {
      cancel();
      window.clearTimeout(settle);
      element.classList.remove('rv', 'in');
      element.style.removeProperty('--d');
    };
  }, [index, reduced]);

  return (
    <Tag ref={ref} className={className}>
      {children}
    </Tag>
  );
}
