"use client";
// Screen 3 — Customer detail: profile, pending dues, package entitlements with
// block-level progress, and visit history.

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Phone, Wallet, Layers, Receipt } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { packagesApi } from "@/lib/api/packages";
import { Button } from "@/components/ui/button";
import { CollectPendingPaymentDialog } from "@/components/customers/collect-pending-payment-dialog";
import { PackageEntitlementCard } from "@/components/packages/PackageEntitlementCard";
import type { PackageSale } from "@/types/package";

interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  total_visits: number;
  total_spent: number; // paise
  pending_balance: number; // paise
  last_visit_at: string | null;
  created_at: string;
}

interface BillRow {
  id: string;
  invoice_number: string | null;
  posted_at: string | null;
  rounded_total: number;
  payment_methods: string[];
}

const rupees = (paise: number) => `₹${(paise / 100).toLocaleString("en-IN")}`;
const fmtDate = (dt: string | null) =>
  dt
    ? new Date(dt).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
    : "—";

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[10px] border border-border-default bg-surface-card px-3 py-2.5">
      <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-0.5 text-[18px] font-semibold tabular-nums text-text-primary">{value}</p>
    </div>
  );
}

const overline = "text-[11px] font-semibold uppercase tracking-[0.06em] text-text-muted";

export default function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [customer, setCustomer] = useState<Customer | null>(null);
  const [sales, setSales] = useState<PackageSale[]>([]);
  const [bills, setBills] = useState<BillRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [collectOpen, setCollectOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const [c, s, b] = await Promise.all([
        apiClient.get<Customer>(`/customers/${id}`),
        packagesApi.listSales({ customer_id: id }),
        apiClient.get<{ items: BillRow[] }>(`/customers/${id}/bills?page=1&size=10`),
      ]);
      setCustomer(c.data);
      setSales(s.data);
      setBills(b.data.items);
    } catch {
      toast.error("Failed to load customer");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="animate-spin text-text-muted" size={24} />
      </div>
    );
  }
  if (!customer) return <div className="p-6 text-text-muted">Customer not found.</div>;

  const name = `${customer.first_name} ${customer.last_name}`.trim();
  const activeSales = sales.filter((s) => s.status === "active" || s.status === "exhausted");

  return (
    <div className="mx-auto max-w-[1100px] space-y-5 p-[22px]">
      <button
        onClick={() => router.push("/dashboard/customers")}
        className="flex items-center gap-1.5 text-[13px] text-text-muted hover:text-text-secondary"
      >
        <ArrowLeft size={15} /> Customers
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-serif text-[28px] leading-tight text-text-primary">{name}</h1>
          {customer.phone && (
            <p className="mt-0.5 flex items-center gap-1.5 text-[13px] text-text-muted">
              <Phone size={13} /> {customer.phone}
            </p>
          )}
        </div>
        {customer.pending_balance > 0 && (
          <Button onClick={() => setCollectOpen(true)}>
            <Wallet size={15} className="mr-1.5" /> Collect {rupees(customer.pending_balance)}
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
        <StatTile label="Visits" value={String(customer.total_visits)} />
        <StatTile label="Total spent" value={rupees(customer.total_spent)} />
        <StatTile
          label="Pending"
          value={rupees(customer.pending_balance)}
        />
        <StatTile label="Member since" value={fmtDate(customer.created_at)} />
      </div>

      {/* Packages */}
      <section className="space-y-2.5">
        <p className={overline}>
          <Layers size={12} className="mr-1 inline" /> Packages · {activeSales.length}
        </p>
        {activeSales.length === 0 ? (
          <p className="rounded-[10px] border border-dashed border-border-default px-4 py-6 text-center text-[13px] text-text-muted">
            No active packages.
          </p>
        ) : (
          <div className="grid gap-2.5 md:grid-cols-2">
            {activeSales.map((sale) => (
              <PackageEntitlementCard key={sale.id} sale={sale} />
            ))}
          </div>
        )}
      </section>

      {/* History */}
      <section className="space-y-2.5">
        <p className={overline}>
          <Receipt size={12} className="mr-1 inline" /> Recent visits
        </p>
        {bills.length === 0 ? (
          <p className="rounded-[10px] border border-dashed border-border-default px-4 py-6 text-center text-[13px] text-text-muted">
            No visits yet.
          </p>
        ) : (
          <div className="overflow-hidden rounded-[10px] border border-border-default">
            <table className="w-full text-[13px]">
              <tbody>
                {bills.map((bill) => (
                  <tr key={bill.id} className="border-b border-border-subtle last:border-0">
                    <td className="px-4 py-2.5 text-text-secondary">{fmtDate(bill.posted_at)}</td>
                    <td className="px-4 py-2.5 text-text-muted">
                      {bill.invoice_number ?? "—"}
                    </td>
                    <td className="px-4 py-2.5 text-text-muted capitalize">
                      {bill.payment_methods.join(" + ") || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium tabular-nums text-text-primary">
                      {rupees(bill.rounded_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <CollectPendingPaymentDialog
        open={collectOpen}
        onClose={() => setCollectOpen(false)}
        customerId={customer.id}
        customerName={name}
        pendingBalance={customer.pending_balance}
        onSuccess={() => {
          setCollectOpen(false);
          load();
        }}
      />
    </div>
  );
}
