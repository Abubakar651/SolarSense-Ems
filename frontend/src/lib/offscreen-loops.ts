/** The element an infinite animation targets, or null for anything that runs a finite number of times. */
function loopTarget(animation: Animation): Element | null {
  const effect = animation.effect as KeyframeEffect | null;
  return effect?.getTiming().iterations === Infinity ? effect.target : null;
}

/** Infinite animations on `target` itself, including those on its pseudo-elements. */
function loopsOn(target: Element): Animation[] {
  return target
    .getAnimations({ subtree: true })
    .filter((animation) => loopTarget(animation) === target);
}

function resume(animation: Animation) {
  if (animation.playState === 'paused') animation.play();
}

/**
 * Looping animations on SVG shapes (dashed flow lines, spinning rays, pulses) cannot run on the
 * compositor, so each one costs main-thread time on every frame even when scrolled out of view.
 * Pauses every infinite animation while its target is off screen and resumes it on return.
 * Returns a function that stops watching and resumes whatever it paused.
 */
export function pauseOffscreenLoops(): () => void {
  const paused = new Set<Animation>();

  const observer = new IntersectionObserver(
    (entries) => {
      for (const { target, isIntersecting } of entries) {
        for (const animation of loopsOn(target)) {
          if (isIntersecting) {
            if (paused.delete(animation)) resume(animation);
          } else if (animation.playState === 'running') {
            animation.pause();
            paused.add(animation);
          }
        }
      }
    },
    // Resume a little before the target scrolls in so the motion is already running when it appears.
    { rootMargin: '80px' },
  );

  for (const animation of document.getAnimations()) {
    const target = loopTarget(animation);
    if (target) observer.observe(target);
  }

  // Loops that start later (a flow line switching on, a panel being shown) are picked up here;
  // re-observing makes the observer report the target's current visibility again.
  const onAnimationStart = ({ target }: Event) => {
    if (!(target instanceof Element) || loopsOn(target).length === 0) return;
    observer.unobserve(target);
    observer.observe(target);
  };
  document.addEventListener('animationstart', onAnimationStart);

  return () => {
    document.removeEventListener('animationstart', onAnimationStart);
    observer.disconnect();
    paused.forEach(resume);
  };
}
