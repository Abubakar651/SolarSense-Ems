/** Legend under the dashboard chart title (decorative: the chart has its own text alternative). */
export function ChartLegend() {
  return (
    <div className="legend" aria-hidden="true">
      <span title="Solar (kW)">
        <i className="sw soft" />
        Solar
      </span>
      <span title="Used directly">
        <i className="sw" style={{ background: 'var(--c-solar)', opacity: 0.45 }} />
        Used
      </span>
      <span title="Usage (kW)">
        <i className="sw line" />
        Usage
      </span>
      <span title="Battery %">
        <i className="sw" />
        Battery %
      </span>
      <span title="Peak hours">
        <i className="sw hatch" />
        Peak
      </span>
    </div>
  );
}
