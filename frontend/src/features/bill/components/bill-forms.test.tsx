import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ToastProvider } from '@/providers/toast-provider';
import type { BillEstimate, BillToolsDefaults, ProsumerComparison } from '@/types/domain/tariff';
import { estimateBillAction } from '../actions';
import { CompareResult } from './bill-results';
import { EstimateCard } from './estimate-card';

// The mock demo has no bill engine: the action answers with no estimate.
vi.mock('../actions', () => ({ estimateBillAction: vi.fn(), compareProsumerAction: vi.fn() }));

const renderCard = (defaults: BillToolsDefaults) =>
  render(
    <ToastProvider>
      <EstimateCard defaults={defaults} />
    </ToastProvider>,
  );

const defaults: BillToolsDefaults = {
  sanctionedLoadKw: 10,
  category: 'TOU_A1B',
  includeElectricityDuty: false,
  isAtlFiler: true,
};

describe('EstimateCard', () => {
  beforeEach(() => {
    vi.mocked(estimateBillAction).mockReset().mockResolvedValue({ ok: true, data: null });
  });

  it('starts from the customer settings', () => {
    renderCard(defaults);
    expect(screen.getByLabelText(/Sanctioned load/)).toHaveValue('10');
    expect(screen.getByLabelText('Tariff category')).toHaveValue('TOU_A1B');
    expect(screen.getByLabelText('Active taxpayer (ATL filer)')).toBeChecked();
    expect(screen.getByLabelText('Include electricity duty')).not.toBeChecked();
  });

  it('asks for peak and off-peak units on a time-of-use bill and total units otherwise', async () => {
    const user = userEvent.setup();
    renderCard(defaults);
    expect(screen.getByLabelText('Peak units (kWh)')).toBeVisible();
    expect(screen.queryByLabelText('Units used (kWh)')).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Tariff category'), 'PROTECTED');
    expect(screen.getByLabelText('Units used (kWh)')).toBeVisible();
    expect(screen.queryByLabelText('Peak units (kWh)')).not.toBeInTheDocument();
  });

  it('rejects a sanctioned load of 0, which the backend refuses', async () => {
    const user = userEvent.setup();
    renderCard(defaults);
    await user.clear(screen.getByLabelText(/Sanctioned load/));
    await user.type(screen.getByLabelText(/Sanctioned load/), '0');
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(screen.getAllByText('Enter a number between 0.1 and 1000.').length).toBeGreaterThan(0);
    expect(screen.queryByText(/not connected yet/)).not.toBeInTheDocument();
  });

  it('accepts valid units and says the calculation is not connected, without inventing a bill', async () => {
    const user = userEvent.setup();
    renderCard(defaults);
    await user.type(screen.getByLabelText('Peak units (kWh)'), '120');
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByText(/not connected yet/)).toBeVisible();
    expect(screen.queryByText(/PKR/)).not.toBeInTheDocument();
  });

  it('sends the form to the bill engine and shows the bill it returns', async () => {
    const estimate: BillEstimate = {
      category: 'TOU_A1B',
      slabId: 'TOU',
      currentTotalKwh: '120',
      lineItems: { peak_energy_charges_pkr: '5622.00' },
      totalPayablePkr: '7890.12',
      totalPayableRoundedRupeePkr: '7890',
      effectiveAllInRatePkrPerKwh: '65.75',
    };
    vi.mocked(estimateBillAction).mockResolvedValue({ ok: true, data: estimate });
    const user = userEvent.setup();
    renderCard(defaults);
    await user.type(screen.getByLabelText('Peak units (kWh)'), '120');
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByRole('heading', { name: /7,890/ })).toBeVisible();
    expect(vi.mocked(estimateBillAction).mock.calls[0]?.[0]).toMatchObject({
      category: 'TOU_A1B',
      sanctionedLoadKw: 10,
      peakKwh: 120,
    });
  });

  it('shows the error when the bill engine fails', async () => {
    vi.mocked(estimateBillAction).mockResolvedValue({
      ok: false,
      code: 'api_unreachable',
      error: 'We couldn’t reach SolarSense. Check your connection and try again.',
    });
    const user = userEvent.setup();
    renderCard(defaults);
    await user.click(screen.getByRole('button', { name: 'Calculate' }));
    expect(await screen.findByText(/couldn’t reach SolarSense/)).toBeInTheDocument();
  });
});

describe('CompareResult', () => {
  const comparison: ProsumerComparison = {
    grandfathered: {
      regime: 'GRANDFATHERED_NET_METERING',
      netBilledPeakImportKwh: '10',
      netBilledOffPeakImportKwh: '0',
      netSurplusExportKwh: '5',
      exportCreditRatePkrPerKwh: '25.32',
      grossRetailImportBillPkr: '1000.00',
      exportCreditPkr: '126.60',
      netPayableAfterCreditsPkr: '873.40',
      closingCreditCarryforwardPkr: '0.00',
    },
    netBilling2026: {
      regime: 'NET_BILLING_2026',
      netBilledPeakImportKwh: '10',
      netBilledOffPeakImportKwh: '0',
      netSurplusExportKwh: '5',
      exportCreditRatePkrPerKwh: '8.13',
      grossRetailImportBillPkr: '1000.00',
      exportCreditPkr: '40.65',
      netPayableAfterCreditsPkr: '959.35',
      closingCreditCarryforwardPkr: '0.00',
    },
    grandfatheredAdvantagePkr: '85.95',
  };

  it('shows both arrangements side by side with the verdict', () => {
    render(<CompareResult request={null} comparison={comparison} />);
    expect(
      screen.getByText('Net metering costs PKR 85.95 less than net billing this month.'),
    ).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Net metering' })).toBeVisible();
    expect(screen.getByText('PKR 25.32/kWh')).toBeVisible();
    expect(screen.getByText('PKR 8.13/kWh')).toBeVisible();
  });
});
