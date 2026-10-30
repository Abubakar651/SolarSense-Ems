import { describe, expect, it } from 'vitest';
import { settingsMock } from '@/services/repositories/settings/settings.mock';
import {
  blackoutError,
  blackoutLength,
  blackoutsEqual,
  isDirty,
  reserveHint,
  toFormValues,
} from './view-model';

const data = await settingsMock.getSettings();

describe('toFormValues', () => {
  const values = toFormValues(data);

  it('keys values by input id', () => {
    expect(values['p-name']).toBe('Zaeem');
    expect(values['t-p']).toBe('46.85');
    expect(values.reserve).toBe('15');
    expect(values.prio).toBe('balanced');
  });

  it('keeps switches as booleans', () => {
    expect(values['rule-peak']).toBe(true);
    expect(values['notify-2-email']).toBe(false);
    expect(values['notify-5-app']).toBe(false);
  });

  it('has an in-app and an email value for every notification', () => {
    data.notifications.forEach((_, index) => {
      expect(typeof values[`notify-${index}-app`]).toBe('boolean');
      expect(typeof values[`notify-${index}-email`]).toBe('boolean');
    });
  });
});

describe('isDirty', () => {
  const saved = toFormValues(data);

  it('is false for identical values', () => {
    expect(isDirty({ ...saved }, saved)).toBe(false);
  });

  it('is true when a text value changes and false again when it is restored', () => {
    expect(isDirty({ ...saved, 'p-name': 'Someone Else' }, saved)).toBe(true);
    expect(isDirty({ ...saved, 'p-name': saved['p-name'] as string }, saved)).toBe(false);
  });

  it('is true when a switch flips', () => {
    expect(isDirty({ ...saved, 'rule-export': false }, saved)).toBe(true);
  });
});

describe('reserveHint', () => {
  it('converts the reserve into hours of backup', () => {
    expect(reserveHint(30, 10)).toBe(
      'About 3.3 hours of typical overnight backup, held back from daily savings.',
    );
    expect(reserveHint(100, 10)).toContain('About 11.1 hours');
  });
});

describe('blackoutError', () => {
  const existing = [{ start: '14:00', end: '16:00' }];

  it('accepts a new window', () => {
    expect(blackoutError('18:00', '20:00', existing)).toBeNull();
  });

  it('accepts a window that crosses midnight', () => {
    expect(blackoutError('22:00', '02:00', existing)).toBeNull();
  });

  it('asks for both times when one is empty', () => {
    expect(blackoutError('', '20:00', existing)).toBe('Choose a start and an end time.');
    expect(blackoutError('18:00', '', existing)).toBe('Choose a start and an end time.');
  });

  it('rejects a window with the same start and end', () => {
    expect(blackoutError('18:00', '18:00', existing)).toBe(
      'Start and end must be different times.',
    );
  });

  it('rejects a window that is already listed', () => {
    expect(blackoutError('14:00', '16:00', existing)).toBe('That blackout is already listed.');
  });
});

describe('blackoutLength', () => {
  it('formats whole and part hours', () => {
    expect(blackoutLength('14:00', '16:00')).toBe('2 h');
    expect(blackoutLength('14:00', '15:30')).toBe('1 h 30 min');
    expect(blackoutLength('14:00', '14:45')).toBe('45 min');
  });

  it('counts across midnight', () => {
    expect(blackoutLength('22:00', '02:00')).toBe('4 h');
  });
});

describe('blackoutsEqual', () => {
  const a = [{ start: '14:00', end: '16:00' }];

  it('is true for the same windows', () => {
    expect(blackoutsEqual(a, [{ start: '14:00', end: '16:00' }])).toBe(true);
  });

  it('is false when a window is added, removed or changed', () => {
    expect(blackoutsEqual(a, [])).toBe(false);
    expect(blackoutsEqual(a, [{ start: '14:00', end: '17:00' }])).toBe(false);
  });
});
