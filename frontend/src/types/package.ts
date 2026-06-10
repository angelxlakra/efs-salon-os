// frontend/src/types/package.ts

export type PackageDefinitionStatus = "draft" | "published" | "archived";
export type EntitlementType = "counted" | "unlimited";
export type Shareability = "owner_only" | "shared";
export type PackageSaleStatus = "active" | "expired" | "refunded" | "exhausted";
export type DiscountMode = "pct" | "flat" | "final";

export interface PackageDefinitionItem {
  id: string;
  service_id: string;
  service_name?: string;
  quantity: number;
  unit_price_paise: number;
  locked: boolean;
  display_order: number;
  max_redemptions: number | null;
}

export interface PackageDefinition {
  id: string;
  name: string;
  description?: string | null;
  status: PackageDefinitionStatus;
  entitlement_type: EntitlementType;
  total_sessions: number | null;
  shareability: Shareability;
  validity_days: number;
  auto_apply: boolean;
  cancellation_fee_pct: string; // Decimal serialized as string
  items: PackageDefinitionItem[];
  created_at: string;
  updated_at: string;
}

export interface PackageDefinitionCreate {
  name: string;
  description?: string;
  entitlement_type: EntitlementType;
  total_sessions?: number;
  shareability: Shareability;
  validity_days: number;
  auto_apply: boolean;
  cancellation_fee_pct: string;
  items: Array<Omit<PackageDefinitionItem, "id" | "service_name">>;
  discount?: { mode: DiscountMode; value: string };
}

// PackageDefinitionCreate is also used for updates
export type PackageDefinitionUpdate = PackageDefinitionCreate;

export interface PackageSaleItem {
  id: string;
  service_id: string;
  service_name?: string;
  quantity: number;
  snapshot_unit_price_paise: number;
  snapshot_gst_rate_pct: string;
  locked: boolean;
  max_redemptions: number | null;
  remaining: number | null;
}

export interface PackageSale {
  id: string;
  bill_id: string;
  package_definition_id: string;
  package_definition_name?: string;
  customer_id: string;
  customer_name?: string;
  selling_staff_id: string | null;
  sold_at: string;
  expires_at: string;
  entitlement_type_snapshot: EntitlementType;
  shareability_snapshot: Shareability;
  cancellation_fee_pct_snapshot: string;
  total_sessions_snapshot: number | null;
  sessions_remaining: number | null;
  status: PackageSaleStatus;
  refunded_at: string | null;
  refund_bill_id: string | null;
  items: PackageSaleItem[];
  created_at: string;
  updated_at: string;
}

export interface PackageSaleSummary {
  id: string;
  package_definition_name?: string | null;
  entitlement_type_snapshot: EntitlementType;
  sessions_remaining: number | null;
  total_sessions_snapshot: number | null;
  expires_at: string;
  shareability_snapshot: Shareability;
  customer_id: string;
  customer_name?: string | null;
}

export interface EligiblePackage {
  package_sale: PackageSaleSummary;
  snapshot_price_paise: number;
}

export interface RefundBreakdown {
  kind: "counted" | "unlimited";
  base_paise: number;
  fee_paise: number;
  refund_paise: number;
  consumed_value_paise: number;
  pct_remaining?: string;
  sessions_consumed?: number;
  sessions_total?: number;
}

export interface RefundResponse {
  credit_note_bill_id: string;
  status: "refunded";
}
