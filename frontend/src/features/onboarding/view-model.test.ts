import { describe, expect, it } from 'vitest';
import {
  LAST_STEP,
  ONBOARDING_STEPS,
  formValues,
  reviewRows,
  toOnboardingRequest,
} from './view-model';

const values = {
  'ob-site': 'My Site',
  'ob-addr': 'Street 1',
  'ob-city': 'Town',
  'ob-pv': '8.0',
  'ob-bat': '10.0',
  'ob-inv': 'GoodWe',
  'ob-sn': 'SN123',
  'ob-cat': 'TOU_A1B',
  'ob-reg': 'NET_BILLING_2026',
  'ob-load': '10',
};

describe('reviewRows', () => {
  it('summarises the entered values in order', () => {
    expect(reviewRows(values)).toEqual([
      { label: 'Site', value: 'My Site' },
      { label: 'Address', value: 'Street 1, Town' },
      { label: 'Solar', value: '8.0 kWp' },
      { label: 'Battery', value: '10.0 kWh' },
      { label: 'Inverter', value: 'GoodWe · SN123' },
      { label: 'Tariff', value: 'Time-of-use A-1(b) · 10 kW · Export 8.13 PKR/kWh' },
    ]);
  });

  it('shows a dash for anything left empty', () => {
    const rows = reviewRows({ ...values, 'ob-sn': '', 'ob-city': '' });
    expect(rows.find((r) => r.label === 'Address')?.value).toBe('Street 1, —');
    expect(rows.find((r) => r.label === 'Inverter')?.value).toBe('GoodWe · —');
  });

  it('derives the export credit from the chosen arrangement, not from typed text', () => {
    const tariff = (reg: string) =>
      reviewRows({ ...values, 'ob-reg': reg }).find((r) => r.label === 'Tariff')?.value;
    expect(tariff('GRANDFATHERED_NET_METERING')).toContain('Export 25.32 PKR/kWh');
    expect(tariff('SINGLE_PHASE_SLAB_ZERO_EXPORT')).toContain('Export 0.00 PKR/kWh');
  });

  it('shows dashes when the tariff choices are missing', () => {
    const rows = reviewRows({ 'ob-site': 'My Site' });
    expect(rows.find((r) => r.label === 'Tariff')?.value).toBe('— · — kW · Export —');
  });
});

describe('wizard steps', () => {
  it('has four steps and the last index matches', () => {
    expect(ONBOARDING_STEPS).toHaveLength(4);
    expect(LAST_STEP).toBe(3);
  });
});

describe('formValues', () => {
  it('reads named inputs as strings', () => {
    const form = document.createElement('form');
    form.innerHTML = '<input name="a" value="1"><select name="b"><option>x</option></select>';
    expect(formValues(form)).toEqual({ a: '1', b: 'x' });
  });
});

describe('toOnboardingRequest', () => {
  it('maps every wizard field to the API body with numbers as numbers', () => {
    expect(toOnboardingRequest(values)).toEqual({
      name: 'My Site',
      address: 'Street 1',
      city: 'Town',
      pv_kwp: 8,
      battery_kwh: 10,
      inverter_make: 'GoodWe',
      inverter_serial: 'SN123',
      tariff_category: values['ob-cat'],
      prosumer_regime: values['ob-reg'],
      sanctioned_load_kw: Number(values['ob-load']),
    });
  });

  it('stores "Other (tell us later)" as Other', () => {
    expect(
      toOnboardingRequest({ ...values, 'ob-inv': 'Other (tell us later)' }).inverter_make,
    ).toBe('Other');
  });
});
