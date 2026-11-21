import { describe, expect, it } from 'vitest';
import { advanceMinute, crossedMidnight } from './sample-clock-provider';

describe('advanceMinute', () => {
  it('adds one minute', () => {
    expect(advanceMinute({ hour: 15, minute: 42 })).toEqual({ hour: 15, minute: 43 });
  });

  it('rolls the hour at :59', () => {
    expect(advanceMinute({ hour: 15, minute: 59 })).toEqual({ hour: 16, minute: 0 });
  });

  it('stops at the end of the sample day', () => {
    expect(advanceMinute({ hour: 23, minute: 59 })).toEqual({ hour: 23, minute: 59 });
  });
});

describe('crossedMidnight', () => {
  it('is true only when the live clock wraps into the next day', () => {
    expect(crossedMidnight({ hour: 23, minute: 59 }, { hour: 0, minute: 0 })).toBe(true);
    expect(crossedMidnight({ hour: 14, minute: 5 }, { hour: 14, minute: 6 })).toBe(false);
  });
});
