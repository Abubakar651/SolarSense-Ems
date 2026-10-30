type Callback = () => void;

let observer: IntersectionObserver | null = null;
const callbacks = new WeakMap<Element, Callback>();

function shared(): IntersectionObserver {
  observer ??= new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const done = callbacks.get(entry.target);
        callbacks.delete(entry.target);
        observer?.unobserve(entry.target);
        done?.();
      }
    },
    { rootMargin: '0px 0px -8% 0px' },
  );
  return observer;
}

/** Calls `onEnter` once when `element` first scrolls into view. Returns a cancel function. */
export function whenInView(element: Element, onEnter: Callback): () => void {
  callbacks.set(element, onEnter);
  shared().observe(element);
  return () => {
    callbacks.delete(element);
    observer?.unobserve(element);
  };
}
