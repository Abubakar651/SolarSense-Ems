'use client';

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react';

export interface TabItem {
  key: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  /** id of the tablist element. */
  id: string;
  /** id of the element wrapping the panels. */
  panelsId: string;
  ariaLabel: string;
  tabs: TabItem[];
}

/**
 * Accessible tabs: roving tabindex, Left/Right (wrapping) and Home/End keys, and an underline
 * that slides to the selected tab. Every panel stays mounted so form state survives switching.
 */
export function Tabs({ id, panelsId, ariaLabel, tabs }: TabsProps) {
  const [selected, setSelected] = useState(tabs[0]?.key);
  const listRef = useRef<HTMLDivElement>(null);
  const indicatorRef = useRef<HTMLSpanElement>(null);
  const placed = useRef(false);

  const placeIndicator = useCallback(() => {
    const indicator = indicatorRef.current;
    const current = listRef.current?.querySelector<HTMLElement>('[aria-selected="true"]');
    if (!indicator || !current?.offsetWidth) return;
    // The first placement jumps into position; later ones slide.
    indicator.style.transition = placed.current ? '' : 'none';
    indicator.style.width = `${current.offsetWidth}px`;
    indicator.style.transform = `translateX(${current.offsetLeft}px)`;
    if (!placed.current) {
      void indicator.offsetWidth;
      indicator.style.transition = '';
      placed.current = true;
    }
  }, []);

  useLayoutEffect(placeIndicator, [selected, placeIndicator]);
  useEffect(() => {
    window.addEventListener('resize', placeIndicator);
    return () => window.removeEventListener('resize', placeIndicator);
  }, [placeIndicator]);

  const onKeyDown = (event: KeyboardEvent, index: number) => {
    const last = tabs.length - 1;
    const target = {
      ArrowRight: index === last ? 0 : index + 1,
      ArrowLeft: index === 0 ? last : index - 1,
      Home: 0,
      End: last,
    }[event.key];
    const next = target === undefined ? undefined : tabs[target];
    if (target === undefined || !next) return;
    event.preventDefault();
    setSelected(next.key);
    listRef.current?.querySelectorAll<HTMLElement>('[role="tab"]')[target]?.focus();
  };

  return (
    <>
      <div className="tabs" role="tablist" aria-label={ariaLabel} id={id} ref={listRef}>
        {tabs.map(({ key, label }, index) => (
          <button
            key={key}
            role="tab"
            aria-selected={key === selected}
            aria-controls={`tp-${key}`}
            id={`tb-${key}`}
            tabIndex={key === selected ? 0 : -1}
            onClick={() => setSelected(key)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {label}
          </button>
        ))}
        <span className="tab-ind" aria-hidden="true" ref={indicatorRef} />
      </div>
      <div id={panelsId}>
        {tabs.map(({ key, content }) => (
          <div
            key={key}
            role="tabpanel"
            id={`tp-${key}`}
            aria-labelledby={`tb-${key}`}
            tabIndex={0}
            hidden={key !== selected}
          >
            {content}
          </div>
        ))}
      </div>
    </>
  );
}
