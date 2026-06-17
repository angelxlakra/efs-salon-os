import { describe, expect, it, beforeEach } from "vitest";
import { useCartStore, computeGstBreakdown, type CartItem } from "@/stores/cart-store";

function svc(over: Partial<CartItem> = {}): Omit<CartItem, "id" | "isBooked"> {
  return {
    serviceId: "s1",
    serviceName: "Bridal Glow",
    isProduct: false,
    quantity: 1,
    unitPrice: 250000,
    discount: 0,
    taxRate: 0,
    ...over,
  };
}

describe("cart redemption math", () => {
  beforeEach(() => useCartStore.getState().clearCart());

  it("excludes a redeemed line from subtotal and total", () => {
    const store = useCartStore.getState();
    store.addItem(svc()); // ₹2500
    store.addItem(svc({ serviceId: "s2", serviceName: "Manicure", unitPrice: 80000 })); // ₹800

    expect(useCartStore.getState().getSubtotal()).toBe(330000);

    // Redeem the Bridal Glow line (qty 1 fully covered)
    const line = useCartStore.getState().items.find((i) => i.serviceId === "s1")!;
    store.setLineRedemption(line.id, {
      packageSaleId: "sale1", packageName: "Aroma Deluxe", coveredQuantity: 1,
    });

    expect(useCartStore.getState().getSubtotal()).toBe(80000); // only the manicure
    expect(useCartStore.getState().getTotal()).toBe(80000);
  });

  it("charges only the uncovered units of a partially-redeemed line", () => {
    const store = useCartStore.getState();
    store.addItem(svc({ serviceId: "s1", unitPrice: 400000, quantity: 3 })); // 3 × ₹4000

    const line = useCartStore.getState().items.find((i) => i.serviceId === "s1")!;
    // Package covers 2 of the 3 units → charge 1 × ₹4000.
    store.setLineRedemption(line.id, {
      packageSaleId: "sale1", packageName: "Lotus", coveredQuantity: 2,
    });

    expect(useCartStore.getState().getSubtotal()).toBe(400000); // 1 unit charged
    expect(useCartStore.getState().getTotal()).toBe(400000);
  });

  it("counts only uncovered units in the GST split breakdown", () => {
    const items: CartItem[] = [
      { id: "a", serviceId: "s1", serviceName: "Lotus", isProduct: false, quantity: 3,
        unitPrice: 400000, discount: 0, taxRate: 5, isBooked: false,
        redemption: { packageSaleId: "x", packageName: "P", coveredQuantity: 2 } },
    ];
    const gst = computeGstBreakdown(items, 0, true);
    expect(gst.serviceSection.subtotal).toBe(400000); // 1 uncovered unit
  });

  it("treats a cart-package redemption like any other for charged units", () => {
    const store = useCartStore.getState();
    store.addItem(svc({ serviceId: "s1", unitPrice: 3000, quantity: 1 }));
    const line = useCartStore.getState().items.find((i) => i.serviceId === "s1")!;
    store.setLineRedemption(line.id, {
      packageSaleId: null, fromDefinitionId: "def1", packageName: "Basic Care", coveredQuantity: 1,
    });
    expect(useCartStore.getState().getSubtotal()).toBe(0);
  });
});
