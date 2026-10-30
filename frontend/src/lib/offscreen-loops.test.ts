import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { pauseOffscreenLoops } from './offscreen-loops';

type Entry = { target: Element; isIntersecting: boolean };

class FakeObserver {
  static current: FakeObserver;
  observed = new Set<Element>();
  observe = vi.fn((element: Element) => this.observed.add(element));
  unobserve = vi.fn((element: Element) => this.observed.delete(element));
  disconnect = vi.fn();
  constructor(readonly report: (entries: Entry[]) => void) {
    FakeObserver.current = this;
  }
}

function animationOn(target: Element, iterations = Infinity) {
  let playState = 'running';
  return {
    get playState() {
      return playState;
    },
    set playState(value: string) {
      playState = value;
    },
    effect: { target, getTiming: () => ({ iterations }) },
    pause: vi.fn(() => {
      playState = 'paused';
    }),
    play: vi.fn(() => {
      playState = 'running';
    }),
  };
}

/** jsdom has no Web Animations API: report `animations` as the ones running on the page. */
function runOnPage(...animations: ReturnType<typeof animationOn>[]) {
  const all = animations as unknown as Animation[];
  document.getAnimations = () => all;
  for (const { effect } of animations) {
    effect.target.getAnimations = () =>
      all.filter((animation) => (animation.effect as KeyframeEffect).target === effect.target);
  }
}

const scrollTo = (target: Element, isIntersecting: boolean) =>
  FakeObserver.current.report([{ target, isIntersecting }]);

describe('pauseOffscreenLoops', () => {
  let target: HTMLElement;

  beforeEach(() => {
    vi.stubGlobal('IntersectionObserver', FakeObserver);
    target = document.body.appendChild(document.createElement('div'));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    target.remove();
  });

  it('pauses a looping animation while its target is off screen and resumes it on return', () => {
    const loop = animationOn(target);
    runOnPage(loop);
    pauseOffscreenLoops();

    scrollTo(target, false);
    expect(loop.pause).toHaveBeenCalledOnce();

    scrollTo(target, true);
    expect(loop.play).toHaveBeenCalledOnce();
  });

  it('does not watch animations that run a finite number of times', () => {
    runOnPage(animationOn(target, 1));
    pauseOffscreenLoops();

    expect(FakeObserver.current.observed.size).toBe(0);
  });

  it('leaves an animation alone that it did not pause', () => {
    const loop = animationOn(target);
    loop.playState = 'paused';
    runOnPage(loop);
    pauseOffscreenLoops();

    scrollTo(target, false);
    scrollTo(target, true);
    expect(loop.pause).not.toHaveBeenCalled();
    expect(loop.play).not.toHaveBeenCalled();
  });

  it('picks up a loop that starts after the first scan', () => {
    runOnPage();
    pauseOffscreenLoops();
    expect(FakeObserver.current.observed.has(target)).toBe(false);

    runOnPage(animationOn(target));
    target.dispatchEvent(new Event('animationstart', { bubbles: true }));
    expect(FakeObserver.current.observed.has(target)).toBe(true);
  });

  it('resumes what it paused and stops watching when cleaned up', () => {
    const loop = animationOn(target);
    runOnPage(loop);
    const stop = pauseOffscreenLoops();
    scrollTo(target, false);

    stop();
    expect(loop.play).toHaveBeenCalledOnce();
    expect(FakeObserver.current.disconnect).toHaveBeenCalledOnce();

    FakeObserver.current.unobserve.mockClear();
    target.dispatchEvent(new Event('animationstart', { bubbles: true }));
    expect(FakeObserver.current.unobserve).not.toHaveBeenCalled();
  });
});
