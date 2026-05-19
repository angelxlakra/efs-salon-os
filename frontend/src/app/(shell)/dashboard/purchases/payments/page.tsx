import { redirect } from "next/navigation";

/**
 * /dashboard/purchases/payments has no index view — redirect to the new payment form.
 * Prevents the 404 that Next.js RSC prefetch logs when a Link to /payments/new is rendered.
 */
export default function PaymentsIndexPage() {
  redirect("/dashboard/purchases/payments/new");
}
