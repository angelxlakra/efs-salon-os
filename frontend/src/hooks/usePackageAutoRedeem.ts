// Live-in-cart package redemption with two-level budget allocation.
//
// Each covered service draws from TWO budgets: its own per-line cap (independent
// per service) and a shared budget pooled across services (the package's global
// session pool, or a choice/pool block counter). We allocate units against both
// so a bundle of distinct services each gets covered (every service has its own
// cap; the shared pool only binds when it's smaller than the sum). The backend
// re-validates and enforces the real limits at checkout.

import { useEffect, useRef } from "react";
import { useCartStore } from "@/stores/cart-store";
import { packagesApi } from "@/lib/api/packages";

interface Elig {
  packageSaleId: string;
  packageName: string;
  lineRemaining: number;
  sharedKey: string | null;
  sharedRemaining: number;
}

export function usePackageAutoRedeem() {
  const items = useCartStore((s) => s.items);
  const customerId = useCartStore((s) => s.customerId);
  const setLineRedemption = useCartStore((s) => s.setLineRedemption);

  const eligByService = useRef<Map<string, Elig | null>>(new Map());
  const inFlight = useRef<Set<string>>(new Set());
  const lastCustomer = useRef<string | null>(null);

  useEffect(() => {
    if (lastCustomer.current !== customerId) {
      lastCustomer.current = customerId;
      eligByService.current.clear();
      inFlight.current.clear();
    }
    if (!customerId) {
      for (const it of items) if (it.redemption) setLineRedemption(it.id, null);
      return;
    }

    const serviceLines = items.filter(
      (it) => !it.isProduct && it.kind !== "package_sale" && !!it.serviceId
    );

    const missing = [
      ...new Set(
        serviceLines
          .map((it) => it.serviceId!)
          .filter((sid) => !eligByService.current.has(sid) && !inFlight.current.has(sid))
      ),
    ];
    if (missing.length > 0) {
      missing.forEach((sid) => inFlight.current.add(sid));
      Promise.all(
        missing.map((sid) =>
          packagesApi
            .checkEligibility({ customer_id: customerId, service_id: sid })
            .then((res) => {
              const e = res.data[0];
              eligByService.current.set(
                sid,
                e
                  ? {
                      packageSaleId: e.package_sale.id,
                      packageName: e.package_sale.package_definition_name ?? "Package",
                      lineRemaining: e.line_remaining,
                      sharedKey: e.shared_budget_key,
                      sharedRemaining: e.shared_remaining,
                    }
                  : null
              );
            })
            .catch(() => eligByService.current.set(sid, null))
            .finally(() => inFlight.current.delete(sid))
        )
      ).then(() => allocate(serviceLines));
      return;
    }

    allocate(serviceLines);

    function allocate(lines: typeof serviceLines) {
      // Per-service line budget (independent) and per-shared-key pool budget.
      const lineBudget = new Map<string, number>(); // service_id -> remaining
      const sharedBudget = new Map<string, number>(); // shared_key -> remaining
      for (const sid of new Set(lines.map((l) => l.serviceId!))) {
        const e = eligByService.current.get(sid);
        if (!e) continue;
        lineBudget.set(sid, e.lineRemaining);
        if (e.sharedKey && !sharedBudget.has(e.sharedKey)) {
          sharedBudget.set(e.sharedKey, e.sharedRemaining);
        }
      }

      for (const line of lines) {
        const e = eligByService.current.get(line.serviceId!);
        let next:
          | { packageSaleId: string; packageName: string; coveredQuantity: number }
          | null = null;
        if (e) {
          const lineLeft = lineBudget.get(line.serviceId!) ?? 0;
          const poolLeft = e.sharedKey
            ? sharedBudget.get(e.sharedKey) ?? 0
            : Number.POSITIVE_INFINITY;
          const covered = Math.min(line.quantity, lineLeft, poolLeft);
          if (covered > 0) {
            next = {
              packageSaleId: e.packageSaleId,
              packageName: e.packageName,
              coveredQuantity: covered,
            };
            lineBudget.set(line.serviceId!, lineLeft - covered);
            if (e.sharedKey) sharedBudget.set(e.sharedKey, poolLeft - covered);
          }
        }
        const cur = line.redemption ?? null;
        const same =
          (cur === null && next === null) ||
          (!!cur &&
            !!next &&
            cur.packageSaleId === next.packageSaleId &&
            cur.coveredQuantity === next.coveredQuantity);
        if (!same) setLineRedemption(line.id, next);
      }
    }
  }, [items, customerId, setLineRedemption]);
}
