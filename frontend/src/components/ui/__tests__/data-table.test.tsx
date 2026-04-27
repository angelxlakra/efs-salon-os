import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataTable, type DataTableColumn } from "@/components/ui/data-table";

type Customer = { id: string; name: string; phone: string; spentPaise: number };
const rows: Customer[] = [
  { id: "1", name: "Priya", phone: "9000000001", spentPaise: 240000 },
  { id: "2", name: "Rajni", phone: "9000000002", spentPaise: 180000 },
];
const columns: DataTableColumn<Customer>[] = [
  { id: "name",  header: "Name",   priority: "high",   accessor: (r) => r.name },
  { id: "phone", header: "Phone",  priority: "medium", accessor: (r) => r.phone },
  { id: "spent", header: "Spent",  priority: "high",   accessor: (r) => `₹${(r.spentPaise / 100).toFixed(2)}`, align: "right" },
];

describe("DataTable", () => {
  it("renders headers and rows", () => {
    render(<DataTable data={rows} columns={columns} getRowId={(r) => r.id} />);
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeInTheDocument();
    // Both desktop table and mobile card are in the DOM (CSS-hidden via Tailwind,
    // but JSDOM doesn't apply class-based stylesheets), so text appears twice.
    expect(screen.getAllByText("Priya").length).toBeGreaterThan(0);
    expect(screen.getAllByText("₹2400.00").length).toBeGreaterThan(0);
  });

  it("renders empty state when data is empty", () => {
    render(
      <DataTable
        data={[]}
        columns={columns}
        getRowId={(r) => r.id}
        emptyState={<div>nothing yet</div>}
      />
    );
    expect(screen.getByText("nothing yet")).toBeInTheDocument();
  });

  it("renders skeleton when loading", () => {
    const { container } = render(
      <DataTable data={[]} columns={columns} getRowId={(r) => r.id} loading />
    );
    expect(container.querySelectorAll("[data-shape='row']").length).toBeGreaterThan(0);
  });

  it("calls onRowClick when row is clicked", async () => {
    const onRowClick = vi.fn();
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(<DataTable data={rows} columns={columns} getRowId={(r) => r.id} onRowClick={onRowClick} />);
    // Click first match (desktop table cell) — mobile card is also in DOM.
    await user.click(screen.getAllByText("Priya")[0]);
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });

  it("activates row on Enter and Space when onRowClick is set (keyboard a11y)", async () => {
    const onRowClick = vi.fn();
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    const { container } = render(
      <DataTable data={rows} columns={columns} getRowId={(r) => r.id} onRowClick={onRowClick} />
    );
    const firstRow = container.querySelector("tbody tr[tabindex='0']") as HTMLElement;
    expect(firstRow).toBeTruthy();

    firstRow.focus();
    await user.keyboard("{Enter}");
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);

    onRowClick.mockClear();
    firstRow.focus();
    await user.keyboard(" ");
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });

  it("does NOT make rows focusable when onRowClick is omitted", () => {
    const { container } = render(<DataTable data={rows} columns={columns} getRowId={(r) => r.id} />);
    expect(container.querySelector("tbody tr[tabindex='0']")).toBeNull();
  });

  it("rowAction click does not bubble to onRowClick (stopPropagation)", async () => {
    const onRowClick = vi.fn();
    const onAction = vi.fn();
    const { default: userEvent } = await import("@testing-library/user-event");
    const user = userEvent.setup();
    render(
      <DataTable
        data={rows}
        columns={columns}
        getRowId={(r) => r.id}
        onRowClick={onRowClick}
        rowAction={() => <button onClick={onAction}>act</button>}
      />
    );
    await user.click(screen.getAllByRole("button", { name: "act" })[0]);
    expect(onAction).toHaveBeenCalled();
    expect(onRowClick).not.toHaveBeenCalled();
  });

  it("uses mobileCard override when provided", () => {
    render(
      <DataTable
        data={rows}
        columns={columns}
        getRowId={(r) => r.id}
        mobileCard={(r) => <span data-testid="custom-card">{r.name}-custom</span>}
      />
    );
    expect(screen.getAllByTestId("custom-card").length).toBe(rows.length);
  });

  it("density='dense' emits h-8 row, density='comfort' emits h-11", () => {
    const { container, rerender } = render(
      <DataTable data={rows} columns={columns} getRowId={(r) => r.id} density="dense" />
    );
    expect(container.querySelector("tbody tr")?.className).toMatch(/h-8/);
    rerender(<DataTable data={rows} columns={columns} getRowId={(r) => r.id} density="comfort" />);
    expect(container.querySelector("tbody tr")?.className).toMatch(/h-11/);
  });

  it("renders null when data is empty AND no emptyState provided", () => {
    const { container } = render(
      <DataTable data={[]} columns={columns} getRowId={(r) => r.id} />
    );
    expect(container.firstChild).toBeNull();
  });
});
