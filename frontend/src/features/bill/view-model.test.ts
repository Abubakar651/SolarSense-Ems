import { describe, expect, it } from 'vitest';
import type { BillEstimate, ProsumerComparison, ProsumerSettlement } from '@/types/domain/tariff';
import {
  advantageSentence,
  comparisonRows,
  estimateRows,
  formatPkr,
  readCompareForm,
  readEstimateForm,
  usesPeakSplit,
} from './view-model';

// Shaped like the backend responses; the figures are made up to exercise formatting only.
const estimate: BillEstimate = {
  category: 'TOU_A1B',
  slabId: 'TOU_A1B',
  currentTotalKwh: '500',
  lineItems: {
    peak_energy_charges_pkr: '9370.00',
    fixed_charges_pkr: '6750.00',
    brand_new_charge_pkr: '12.50',
  },
  totalPayablePkr: '16132.50',
  totalPayableRoundedRupeePkr: '16133',
  effectiveAllInRatePkrPerKwh: '32.27',
};

const settlement = (overrides: Partial<ProsumerSettlement> = {}): ProsumerSettlement => ({
  regime: 'GRANDFATHERED_NET_METERING',
  netBilledPeakImportKwh: '100',
  netBilledOffPeakImportKwh: '0',
  netSurplusExportKwh: '40.5',
  exportCreditRatePkrPerKwh: '25.32',
  grossRetailImportBillPkr: '6000.00',
  exportCreditPkr: '1025.46',
  netPayableAfterCreditsPkr: '4974.54',
  closingCreditCarryforwardPkr: '0.00',
  ...overrides,
});

const comparison = (advantage: string): ProsumerComparison => ({
  grandfathered: settlement(),
  netBilling2026: settlement({ regime: 'NET_BILLING_2026', exportCreditRatePkrPerKwh: '8.13' }),
  grandfatheredAdvantagePkr: advantage,
});

describe('formatPkr', () => {
  it('groups thousands and keeps the backend digits', () => {
    expect(formatPkr('16132.50')).toBe('PKR 16,132.50');
    expect(formatPkr('1234567')).toBe('PKR 1,234,567');
    expect(formatPkr('0.00')).toBe('PKR 0.00');
  });

  it('keeps the sign in front', () => {
    expect(formatPkr('-250.00')).toBe('-PKR 250.00');
  });
});

describe('estimateRows', () => {
  it('labels known lines and falls back to a readable name for new ones', () => {
    expect(estimateRows(estimate)).toEqual([
      ['Peak energy', 'PKR 9,370.00'],
      ['Fixed charges', 'PKR 6,750.00'],
      ['Brand new charge', 'PKR 12.50'],
    ]);
  });
});

describe('comparisonRows', () => {
  it('gives the net-metering figure first and the net-billing figure second', () => {
    const rows = comparisonRows(comparison('3000.00'));
    expect(rows).toHaveLength(8);
    expect(rows.find(([label]) => label === 'Export credit rate')).toEqual([
      'Export credit rate',
      'PKR 25.32/kWh',
      'PKR 8.13/kWh',
    ]);
  });
});

describe('advantageSentence', () => {
  it('says net metering costs less when the advantage is positive', () => {
    expect(advantageSentence(comparison('3000.00'))).toBe(
      'Net metering costs PKR 3,000.00 less than net billing this month.',
    );
  });

  it('says net billing costs less when the advantage is negative', () => {
    expect(advantageSentence(comparison('-120.50'))).toBe(
      'Net billing costs PKR 120.50 less than net metering this month.',
    );
  });

  it('says so when they cost the same', () => {
    expect(advantageSentence(comparison('0.00'))).toBe(
      'Both arrangements cost the same this month.',
    );
  });
});

describe('forms', () => {
  function formWith(html: string): HTMLFormElement {
    const form = document.createElement('form');
    form.innerHTML = html;
    return form;
  }

  it('reads the estimate form, counting empty units as 0 and unticked boxes as false', () => {
    const form = formWith(`
      <select name="bill-cat"><option value="TOU_A1B" selected>x</option></select>
      <input name="bill-load" value="10"><input name="bill-peak" value="120.5">
      <input name="bill-off" value=""><input name="bill-atl" type="checkbox" checked>
      <input name="bill-duty" type="checkbox">`);
    expect(readEstimateForm(form)).toEqual({
      category: 'TOU_A1B',
      sanctionedLoadKw: 10,
      currentKwh: 0,
      peakKwh: 120.5,
      offPeakKwh: 0,
      fpaReference2mPriorKwh: 0,
      includeElectricityDuty: false,
      isAtlFiler: true,
    });
  });

  it('reads the comparison form', () => {
    const form = formWith(
      '<input name="cmp-load" value="10"><input name="cmp-peak" value="80"><input name="cmp-exp" value="300">',
    );
    expect(readCompareForm(form)).toMatchObject({
      sanctionedLoadKw: 10,
      grossPeakImportKwh: 80,
      grossOffPeakImportKwh: 0,
      grossExportKwh: 300,
    });
  });

  it('prices only time-of-use bills from the peak split', () => {
    expect(usesPeakSplit('TOU_A1B')).toBe(true);
    expect(usesPeakSplit('PROTECTED')).toBe(false);
    expect(usesPeakSplit('PREPAID_A1C')).toBe(false);
  });
});
