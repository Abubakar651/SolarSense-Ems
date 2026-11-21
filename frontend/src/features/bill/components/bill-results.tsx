import { DataTable } from '@/components/ui/data-table';
import type {
  BillEstimate,
  BillEstimateRequest,
  ProsumerCompareRequest,
  ProsumerComparison,
} from '@/types/domain/tariff';
import { advantageSentence, comparisonRows, estimateRows, formatPkr } from '../view-model';

function NotConnected() {
  return <p className="muted small">Bill server not connected yet.</p>;
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
      {!request && <p className="muted small">Enter units, then Calculate.</p>}
      {request && !estimate && <NotConnected />}
      {estimate && (
        <>
          <h3>{formatPkr(estimate.totalPayablePkr)}</h3>
          <p className="muted small" style={{ marginBottom: 'var(--sp-3)' }}>
            {`${formatPkr(estimate.effectiveAllInRatePkrPerKwh)}/unit all-in · ${estimate.currentTotalKwh} units · rounded ${formatPkr(estimate.totalPayableRoundedRupeePkr)}`}
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
      {!request && <p className="muted small">Enter units, then Compare.</p>}
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
