// frontend/src/types/service.ts
// Canonical type for a catalog service item, shared across calendar, packages,
// and any other feature that consumes GET /catalog/services.

export interface ServiceItem {
  id: string;
  name: string;
  base_price: number; // paise
  duration_minutes: number;
  category_name: string; // flattened from category.name, "Uncategorized" when null
}

// Kept for backwards-compat — prefer ServiceItem
export type Service = ServiceItem;
