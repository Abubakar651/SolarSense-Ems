import { describe, expect, it } from 'vitest';
import { settingsMock } from '@/services/repositories/settings/settings.mock';
import { isDirty, reserveHint, toFormValues } from './view-model';

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
