import { describe, expect, it } from 'vitest';
import { settingsMock } from '@/services/repositories/settings/settings.mock';
import {
  blackoutError,
  blackoutLength,
  blackoutsEqual,
  isDirty,
  reserveHint,
  toFormValues,
  toSettingsUpdate,
} from './view-model';

const data = await settingsMock.getSettings();

describe('toFormValues', () => {
  const values = toFormValues(data);

  it('keys values by input id', () => {
    expect(values['p-name']).toBe('Zaeem');
    expect(values['t-cat']).toBe('TOU_A1B');
    expect(values['t-reg']).toBe('GRANDFATHERED_NET_METERING');
    expect(values['t-load']).toBe('10');
    expect(values.reserve).toBe('15');
  });

  it('keeps switches as booleans', () => {
    expect(values['t-atl']).toBe(true);
    expect(values['t-duty']).toBe(false);
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
    expect(isDirty({ ...saved, 't-duty': true }, saved)).toBe(true);
  });
});

describe('reserveHint', () => {
  it("converts the reserve into hours of backup at the home's own overnight usage", () => {
    // 3 kWh held, 95% of it delivered, at 0.6 kW.
    expect(reserveHint(30, 10, 0.6)).toBe(
      'About 4.8 hours of backup at your usual overnight usage, held back from daily savings.',
    );
    expect(reserveHint(30, 10, 1.2)).toContain('About 2.4 hours');
  });

  it('shows the reserve as energy when there is no usage to size it by', () => {
    expect(reserveHint(30, 10, null)).toBe(
      'Holds 3.0 kWh for outages, held back from daily savings.',
    );
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

describe('toSettingsUpdate', () => {
  const values = toFormValues(data);

  it('sends numbers as numbers and trims text', () => {
    const update = toSettingsUpdate(
      { ...values, 's-pv': '8.50', 'p-name': '  Zaeem  ' },
      [],
      data.notifications,
    );
    expect(update.site.pv_kwp).toBe(8.5);
    expect(update.reserve_pct).toBe(data.battery.reservePct);
    expect(update.tariff.sanctioned_load_kw).toBe(10);
    expect(update.profile.name).toBe('Zaeem');
  });

  it('keys notification choices by alert type, not position', () => {
    const update = toSettingsUpdate({ ...values, 'notify-2-email': true }, [], data.notifications);
    expect(update.notifications[2]).toEqual({ key: 'peak_soon', in_app: true, email: true });
    expect(update.notifications.map((n) => n.key)).toEqual(data.notifications.map((n) => n.key));
  });

  it('includes the blackout windows being edited', () => {
    const windows = [{ start: '22:00', end: '02:00' }];
    expect(toSettingsUpdate(values, windows, data.notifications).blackouts).toEqual(windows);
  });

  it('reads unset switches as off', () => {
    const update = toSettingsUpdate({ ...values, 't-atl': '' }, [], data.notifications);
    expect(update.tariff.is_atl_filer).toBe(false);
  });

  it('sends the trimmed inverter address', () => {
    const update = toSettingsUpdate(
      { ...values, 's-host': ' 192.168.1.50 ' },
      [],
      data.notifications,
    );
    expect(update.site.inverter_host).toBe('192.168.1.50');
  });

  it('sends a blank inverter address as null, which disconnects the inverter', () => {
    const update = toSettingsUpdate({ ...values, 's-host': '  ' }, [], data.notifications);
    expect(update.site.inverter_host).toBeNull();
  });
});
