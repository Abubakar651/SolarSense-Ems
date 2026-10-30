/** Smoothly scrolls to a section and moves focus into it (reduced motion jumps instead). */
export function scrollToSection(id: string): void {
  const target = document.getElementById(id);
  if (!target) return;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  target.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth' });
  target.setAttribute('tabindex', '-1');
  target.focus({ preventScroll: true });
}
