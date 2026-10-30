import { describe, expect, it } from 'vitest';
import { niceMax } from './nice-max';
import { smooth, smoothArea, type Point } from './smooth';

describe('niceMax', () => {
  it.each([
    [0.9, 4, { step: 0.25, max: 1 }],
    [100, 4, { step: 25, max: 100 }],
    [123, 4, { step: 50, max: 200 }],
    [560, 4, { step: 200, max: 800 }],
    [16000, 4, { step: 5000, max: 20000 }],
  ])('rounds %s up to a friendly axis (%s steps)', (value, steps, expected) => {
    expect(niceMax(value, steps)).toEqual(expected);
  });
});

describe('smooth', () => {
  it('returns an empty path for no points', () => {
    expect(smooth([])).toBe('');
  });

  it('draws straight segments for fewer than three points', () => {
    expect(
      smooth([
        [0, 0],
        [10, 5],
      ]),
    ).toBe('M0,0 L10,5');
  });

  it('starts at the first point and ends at the last', () => {
    const points: Point[] = [
      [0, 10],
      [10, 4],
      [20, 8],
      [30, 2],
    ];
    const path = smooth(points);
    expect(path.startsWith('M0,10')).toBe(true);
    expect(path.endsWith('30,2')).toBe(true);
    expect(path.match(/C/g)).toHaveLength(3);
  });

  it('keeps flat runs flat (no overshoot below a plateau)', () => {
    const path = smooth([
      [0, 5],
      [10, 5],
      [20, 5],
      [30, 1],
    ]);
    // Every control point of the flat first two segments stays on y = 5.
    const firstTwo = path.split(' C').slice(1, 3).join(' ');
    expect(firstTwo.match(/,(-?[\d.]+)/g)?.every((y) => y === ',5')).toBe(true);
  });

  it('never puts a control point above the highest or below the lowest sample', () => {
    const ys = [0, 0, 1, 4, 9, 9, 2, 0];
    const points: Point[] = ys.map((y, i) => [i * 10, y]);
    const controlYs = [...smooth(points).matchAll(/,(-?[\d.]+)/g)].map((m) => Number(m[1]));
    expect(Math.min(...controlYs)).toBeGreaterThanOrEqual(0);
    expect(Math.max(...controlYs)).toBeLessThanOrEqual(9);
  });
});

describe('smoothArea', () => {
  it('closes the path down to the baseline', () => {
    const area = smoothArea(
      [
        [0, 4],
        [10, 2],
        [20, 6],
      ],
      9,
    );
    expect(area.endsWith('L20,9 L0,9Z')).toBe(true);
  });
});
