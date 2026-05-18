import * as React from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

export type ColumnPriority = "high" | "medium" | "low";

export type DataTableColumn<T> = {
  id: string;
  header: string;
  priority: ColumnPriority;
  accessor: (row: T) => React.ReactNode;
  align?: "left" | "right" | "center";
  format?: "money" | "default";
};

type Props<T> = {
  data: T[];
  columns: DataTableColumn<T>[];
  getRowId: (row: T) => string;
  emptyState?: React.ReactNode;
  loading?: boolean;
  onRowClick?: (row: T) => void;
  rowAction?: (row: T) => React.ReactNode;
  density?: "default" | "dense" | "comfort";
  /** Override the default card-from-high-priority-columns mobile view. */
  mobileCard?: (row: T) => React.ReactNode;
};

export function DataTable<T>({
  data,
  columns,
  getRowId,
  emptyState,
  loading,
  onRowClick,
  rowAction,
  density = "default",
  mobileCard,
}: Props<T>) {
  if (loading) {
    return (
      <div className="flex flex-col gap-2" aria-busy>
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} shape="row" />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return emptyState ? <>{emptyState}</> : null;
  }

  const visibleColumns = columns.filter((c) => c.priority !== "low");
  const rowHeight = density === "dense" ? "h-8" : density === "comfort" ? "h-11" : "h-9";

  // Keyboard activation for clickable rows: Enter or Space triggers onRowClick.
  // Bound per-row so the closure captures the current row.
  const handleRowKey = (row: T) => (e: React.KeyboardEvent) => {
    if (onRowClick && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onRowClick(row);
    }
  };

  return (
    <>
      {/* Desktop / tablet table */}
      <div className="hidden sm:block rounded-lg border border-border-subtle overflow-hidden bg-surface-card">
        <table className="w-full border-collapse">
          <thead className="bg-surface-row-hover">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.id}
                  className={cn(
                    "px-4 py-2 text-overline text-text-secondary border-b border-border-subtle",
                    col.align === "right" && "text-right",
                    col.align === "center" && "text-center",
                    col.align !== "right" && col.align !== "center" && "text-left",
                    col.priority === "low" && "hidden lg:table-cell"
                  )}
                >
                  {col.header}
                </th>
              ))}
              {rowAction && <th className="w-10" />}
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr
                key={getRowId(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={onRowClick ? handleRowKey(row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                className={cn(
                  rowHeight,
                  "border-b border-border-subtle last:border-0",
                  onRowClick && "cursor-pointer hover:bg-surface-row-hover focus:outline-none focus:bg-surface-row-hover"
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.id}
                    className={cn(
                      "px-4 text-body-sm text-text-primary",
                      col.align === "right" && "text-right tabular",
                      col.align === "center" && "text-center",
                      col.format === "money" && "tabular",
                      col.priority === "low" && "hidden lg:table-cell"
                    )}
                  >
                    {col.accessor(row)}
                  </td>
                ))}
                {rowAction && (
                  <td className="pr-2 text-right" onClick={(e) => e.stopPropagation()}>
                    {rowAction(row)}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile card fallback */}
      <div className="sm:hidden flex flex-col gap-2">
        {data.map((row) => (
          <div
            key={getRowId(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            onKeyDown={onRowClick ? handleRowKey(row) : undefined}
            tabIndex={onRowClick ? 0 : undefined}
            role={onRowClick ? "button" : undefined}
            className={cn(
              "rounded-lg border border-border-subtle bg-surface-card p-3",
              onRowClick && "cursor-pointer active:bg-surface-row-hover focus:outline-none focus:bg-surface-row-hover"
            )}
          >
            {mobileCard ? (
              mobileCard(row)
            ) : (
              <div className="flex flex-col gap-1">
                {visibleColumns.map((col) => (
                  <div key={col.id} className="flex justify-between gap-3">
                    <span className="text-caption text-text-muted">{col.header}</span>
                    <span
                      className={cn(
                        "text-body-sm text-text-primary",
                        (col.align === "right" || col.format === "money") && "tabular"
                      )}
                    >
                      {col.accessor(row)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
