import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SAMPLE_PEAK_WINDOWS } from '@/services/mock/tariff-windows';
import { SettingsFormProvider } from './settings-form';
import { TariffPanel } from './tariff-panel';

function setup(regime: string) {
  render(
    <SettingsFormProvider
      value={{
        values: {
          't-cat': 'TOU_A1B',
          't-reg': regime,
          't-load': '10',
          't-atl': true,
          't-duty': false,
          't-prot': false,
        },
        set: () => undefined,
      }}
    >
      <TariffPanel peakWindows={SAMPLE_PEAK_WINDOWS} />
    </SettingsFormProvider>,
  );
}

describe('TariffPanel', () => {
  it('offers the five backend tariff categories', () => {
    setup('GRANDFATHERED_NET_METERING');
    const options = within(screen.getByLabelText('Tariff category')).getAllByRole('option');
    expect(options.map((o) => (o as HTMLOptionElement).value)).toEqual([
      'LIFELINE',
      'PROTECTED',
      'UNPROTECTED',
      'TOU_A1B',
      'PREPAID_A1C',
    ]);
  });

  it('offers the three export arrangements and no flat-rate plan', () => {
    setup('GRANDFATHERED_NET_METERING');
    const options = within(screen.getByLabelText('Solar export arrangement')).getAllByRole(
      'option',
    );
    expect(options).toHaveLength(3);
    expect(screen.queryByText(/flat rate/i)).not.toBeInTheDocument();
  });

  it.each([
    ['GRANDFATHERED_NET_METERING', '25.32'],
    ['NET_BILLING_2026', '8.13'],
    ['SINGLE_PHASE_SLAB_ZERO_EXPORT', '0.00'],
  ])('derives the export credit from the %s arrangement', (regime, credit) => {
    setup(regime);
    expect(screen.getByLabelText('Export credit (PKR/kWh)')).toHaveValue(credit);
  });

  it('shows the fixed seasonal peak hours instead of editable times', () => {
    setup('GRANDFATHERED_NET_METERING');
    expect(screen.getByText('17:00 – 21:00')).toBeVisible();
    expect(screen.getByText('19:00 – 23:00')).toBeVisible();
    expect(screen.queryByLabelText('Peak starts')).not.toBeInTheDocument();
  });
});
