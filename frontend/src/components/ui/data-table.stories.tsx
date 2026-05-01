import type { Meta, StoryObj } from "@storybook/react";
import { DataTable, type DataTableColumn } from "./data-table";

type Bill = { id: string; number: string; customer: string; amountPaise: number; status: "paid" | "pending" };

const rows: Bill[] = [
  { id: "1", number: "SAL-25-0171", customer: "Priya Sharma",  amountPaise: 240000, status: "paid" },
  { id: "2", number: "SAL-25-0172", customer: "Rajni Gupta",   amountPaise: 180000, status: "pending" },
  { id: "3", number: "SAL-25-0173", customer: "Anjali Patel",  amountPaise: 320000, status: "paid" },
];
const cols: DataTableColumn<Bill>[] = [
  { id: "number",   header: "Bill",      priority: "high",   accessor: (r) => r.number },
  { id: "customer", header: "Customer",  priority: "high",   accessor: (r) => r.customer },
  { id: "amount",   header: "Amount",    priority: "high",   accessor: (r) => `₹${(r.amountPaise / 100).toFixed(2)}`, align: "right", format: "money" },
  { id: "status",   header: "Status",    priority: "medium", accessor: (r) => r.status },
];

const meta: Meta<typeof DataTable<Bill>> = { title: "UI/DataTable" };
export default meta;

export const Default: StoryObj<typeof DataTable<Bill>> = {
  render: () => <div className="w-[720px]"><DataTable data={rows} columns={cols} getRowId={(r) => r.id} /></div>,
};
export const Loading: StoryObj<typeof DataTable<Bill>> = {
  render: () => <div className="w-[720px]"><DataTable data={[]} columns={cols} getRowId={(r) => r.id} loading /></div>,
};
export const Empty: StoryObj<typeof DataTable<Bill>> = {
  render: () => (
    <div className="w-[720px]">
      <DataTable
        data={[]}
        columns={cols}
        getRowId={(r) => r.id}
        emptyState={<div className="p-8 text-center text-text-muted">No bills match your filter.</div>}
      />
    </div>
  ),
};
