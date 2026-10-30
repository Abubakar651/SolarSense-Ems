import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

export interface TableColumn {
  label: string;
  /** Right-align numeric columns. */
  right?: boolean;
  /** Header text for assistive tech only (icon-only columns). */
  srOnly?: boolean;
}

interface DataTableProps {
  columns: TableColumn[];
  rows: ReactNode[][];
  /** Visually hidden header text for icon-only columns. */
  srOnlyLabels?: boolean;
}

/** Scrolls sideways inside its own box so narrow screens never overflow the page. */
export function DataTable({ columns, rows }: DataTableProps) {
  return (
    <div className="tbl-wrap">
      <table className="tbl num">
        <TableBody columns={columns} rows={rows} />
      </table>
    </div>
  );
}

function TableBody({ columns, rows }: DataTableProps) {
  return (
    <>
      <thead>
        <tr>
          {/* An sr-only header is not right-aligned: its hidden label would sit past the table edge and widen the page. */}
          {columns.map(({ label, right, srOnly }) => (
            <th key={label} className={cn(right && !srOnly && 'r')}>
              {srOnly ? <span className="sr-only">{label}</span> : label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((cells, rowIndex) => (
          <tr key={rowIndex}>
            {cells.map((cell, i) => (
              <td key={i} className={cn(columns[i]?.right && 'r')}>
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </>
  );
}

/** Table behind a "View as table" disclosure: the text alternative to a chart. */
export function ChartTable({ columns, rows }: DataTableProps) {
  return (
    <details className="alt">
      <summary>View as table</summary>
      <DataTable columns={columns} rows={rows} />
    </details>
  );
}
