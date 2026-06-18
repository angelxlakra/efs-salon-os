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
import { usePackagesStore } from "@/stores/packages-store";
import { definitionServiceBudgets } from "@/lib/packages/definition-budget";

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
  const definitions = usePackagesStore((s) => s.definitions);

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
      const lineBudget = new Map<string, number>();
      const sharedBudget = new Map<string, number>();
      for (const sid of new Set(lines.map((l) => l.serviceId!))) {
        const e = eligByService.current.get(sid);
        if (!e) continue;
        lineBudget.set(sid, e.lineRemaining);
        if (e.sharedKey && !sharedBudget.has(e.sharedKey)) sharedBudget.set(e.sharedKey, e.sharedRemaining);
      }

      // Cart packages being sold this checkout — budgets from their definitions.
      const cartPkgs = items.filter((it) => it.kind === "package_sale" && it.packageDefinitionId);
      const cartBudgets = cartPkgs.map((p) => {
        const def = definitions?.find((d) => d.id === p.packageDefinitionId);
        return {
          definitionId: p.packageDefinitionId!,
          packageName: p.packageName ?? "Package",
          budgets: def?.blocks ? definitionServiceBudgets(def.id, def.blocks) : new Map(),
        };
      });
      const cartLineBudget = new Map<string, number>();   // `${defId}:${sid}`
      const cartSharedBudget = new Map<string, number>(); // sharedKey

      for (const line of lines) {
        const sid = line.serviceId!;
        let coveredByOwned = 0;
        let next:
          | { packageSaleId: string | null; fromDefinitionId?: string; packageName: string; coveredQuantity: number }
          | null = null;

        // 1) Owned package first.
        const e = eligByService.current.get(sid);
        if (e) {
          const lineLeft = lineBudget.get(sid) ?? 0;
          const poolLeft = e.sharedKey ? sharedBudget.get(e.sharedKey) ?? 0 : Infinity;
          coveredByOwned = Math.min(line.quantity, lineLeft, poolLeft);
          if (coveredByOwned > 0) {
            next = { packageSaleId: e.packageSaleId, packageName: e.packageName, coveredQuantity: coveredByOwned };
            lineBudget.set(sid, lineLeft - coveredByOwned);
            if (e.sharedKey) sharedBudget.set(e.sharedKey, poolLeft - coveredByOwned);
          }
        }

        // 2) Cart package covers the remaining units.
        let remaining = line.quantity - coveredByOwned;
        if (remaining > 0) {
          for (const cp of cartBudgets) {
            const sb = (cp.budgets as Map<string, { lineRemaining: number; sharedKey: string | null; sharedRemaining: number }>).get(sid);
            if (!sb) continue;
            const lk = `${cp.definitionId}:${sid}`;
            if (!cartLineBudget.has(lk)) cartLineBudget.set(lk, sb.lineRemaining);
            const sk = sb.sharedKey;
            if (sk && !cartSharedBudget.has(sk)) cartSharedBudget.set(sk, sb.sharedRemaining);
            const lineLeft = cartLineBudget.get(lk)!;
            const poolLeft = sk ? cartSharedBudget.get(sk)! : Infinity;
            const cover = Math.min(remaining, lineLeft, poolLeft);
            if (cover > 0) {
              cartLineBudget.set(lk, lineLeft - cover);
              if (sk) cartSharedBudget.set(sk, poolLeft - cover);
              next = {
                packageSaleId: null,
                fromDefinitionId: cp.definitionId,
                packageName: cp.packageName,
                coveredQuantity: coveredByOwned + cover,
              };
              remaining -= cover;
              break;
            }
          }
        }

        const cur = line.redemption ?? null;
        const same =
          (cur === null && next === null) ||
          (!!cur && !!next &&
            cur.packageSaleId === next.packageSaleId &&
            (cur.fromDefinitionId ?? null) === (next.fromDefinitionId ?? null) &&
            cur.coveredQuantity === next.coveredQuantity);
        if (!same) setLineRedemption(line.id, next);
      }
    }
  }, [items, customerId, setLineRedemption, definitions]);
}
