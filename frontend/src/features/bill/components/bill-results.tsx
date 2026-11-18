import { DataTable } from '@/components/ui/data-table';
import type {
  BillEstimate,
  BillEstimateRequest,
  ProsumerCompareRequest,
  ProsumerComparison,
} from '@/types/domain/tariff';
import { advantageSentence, comparisonRows, estimateRows, formatPkr } from '../view-model';

function NotConnected() {
  return (
    <p className="muted small">
      Your figures are valid. The bill calculator runs on the SolarSense server, which is not
      connected yet, so there is no result to show.
    </p>
  );
}

/** `estimate` is null until the backend is connected: the browser cannot work out a LESCO bill. */
export function EstimateResult({
  request,
  estimate,
}: {
  request: BillEstimateRequest | null;
  estimate: BillEstimate | null;
}) {
  return (
    <div aria-live="polite" style={{ marginTop: 'var(--sp-4)' }}>
      {!request && (
        <p className="muted small">Enter your units and choose Calculate to see the bill.</p>
      )}
      {request && !estimate && <NotConnected />}
      {estimate && (
        <>
          <h3>{formatPkr(estimate.totalPayablePkr)}</h3>
          <p className="muted small" style={{ marginBottom: 'var(--sp-3)' }}>
            {`About ${formatPkr(estimate.effectiveAllInRatePkrPerKwh)} per unit, all charges included, for ${estimate.currentTotalKwh} units. Rounded: ${formatPkr(estimate.totalPayableRoundedRupeePkr)}.`}
          </p>
          <DataTable
            columns={[{ label: 'Charge' }, { label: 'Amount', right: true }]}
            rows={estimateRows(estimate)}
          />
        </>
      )}
    </div>
  );
}

export function CompareResult({
  request,
  comparison,
}: {
  request: ProsumerCompareRequest | null;
  comparison: ProsumerComparison | null;
}) {
  return (
    <div aria-live="polite" style={{ marginTop: 'var(--sp-4)' }}>
      {!request && (
        <p className="muted small">Enter a month&apos;s units and choose Compare to see both.</p>
      )}
      {request && !comparison && <NotConnected />}
      {comparison && (
        <>
          <h3>{advantageSentence(comparison)}</h3>
          <DataTable
            columns={[
              { label: 'This month' },
              { label: 'Net metering', right: true },
              { label: 'Net billing', right: true },
            ]}
            rows={comparisonRows(comparison)}
          />
        </>
      )}
    </div>
  );
}
