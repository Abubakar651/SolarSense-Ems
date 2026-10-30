import { describe, expect, it } from 'vitest';
import { LAST_STEP, ONBOARDING_STEPS, formValues, reviewRows } from './view-model';

const values = {
  'ob-site': 'My Site',
  'ob-addr': 'Street 1',
  'ob-city': 'Town',
  'ob-pv': '8.0',
  'ob-bat': '10.0',
  'ob-inv': 'GoodWe',
  'ob-sn': 'SN123',
  'ob-peak': '48.00',
  'ob-off': '35.00',
  'ob-exp': '27.00',
};

describe('reviewRows', () => {
  it('summarises the entered values in order', () => {
    expect(reviewRows(values)).toEqual([
      { label: 'Site', value: 'My Site' },
      { label: 'Address', value: 'Street 1, Town' },
      { label: 'Solar', value: '8.0 kWp' },
      { label: 'Battery', value: '10.0 kWh' },
      { label: 'Inverter', value: 'GoodWe · SN123' },
      { label: 'Tariff', value: 'Peak 48.00 · Off-peak 35.00 · Export 27.00 PKR/kWh' },
    ]);
  });

  it('shows a dash for anything left empty', () => {
    const rows = reviewRows({ ...values, 'ob-sn': '', 'ob-city': '' });
    expect(rows.find((r) => r.label === 'Address')?.value).toBe('Street 1, —');
    expect(rows.find((r) => r.label === 'Inverter')?.value).toBe('GoodWe · —');
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
