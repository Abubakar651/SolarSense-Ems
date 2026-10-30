/** Legend under the dashboard chart title (decorative: the chart has its own text alternative). */
export function ChartLegend() {
  return (
    <div className="legend" aria-hidden="true">
      <span>
        <i className="sw soft" />
        Solar kW
      </span>
      <span>
        <i className="sw" style={{ background: 'var(--c-solar)', opacity: 0.45 }} />
        Used directly
      </span>
      <span>
        <i className="sw line" />
        Usage kW
      </span>
      <span>
        <i className="sw" />
        Battery %
      </span>
      <span>
        <i className="sw hatch" />
        Peak hours
      </span>
    </div>
  );
}
