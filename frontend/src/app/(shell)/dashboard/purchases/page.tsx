import { redirect } from "next/navigation";

/**
 * /dashboard/purchases has no index view — redirect to the invoices sub-page.
 * Removes the 404 that RSC prefetch logs when the nav item is hovered.
 */
export default function PurchasesIndexPage() {
  redirect("/dashboard/purchases/invoices");
}
