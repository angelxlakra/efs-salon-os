// frontend/src/types/package.ts

export type PackageDefinitionStatus = "draft" | "published" | "archived";
export type EntitlementType = "counted" | "unlimited";
export type Shareability = "owner_only" | "shared";
export type PackageSaleStatus = "active" | "expired" | "refunded" | "exhausted";
export type DiscountMode = "pct" | "flat" | "final";

// ---------------------------------------------------------------------------
// Package Builder v2 — entitlement blocks
//
// A package is a stack of blocks. Each block kind carries its own entitlement
// semantics (replacing the old package-level `entitlement_type`). These are the
// BUILDER-SIDE draft shapes: money lives in paise (integers, per project rule),
// while small count fields (picks/sessions/daily_cap/quantity) are held as
// strings during editing — see the NumericCell draft-while-focused pattern.
// ---------------------------------------------------------------------------

export type BlockKind = "items" | "choice" | "unlimited" | "pool" | "credit";
export type ChooseAt = "purchase" | "visit";
export type CreditScope = "any" | "services" | "retail";

export interface ItemsRow {
  service_id: string;
  service_name: string; // display only
  quantity: string; // count, edited as string
  unit_price_paise: number;
}

export interface ChoiceRow {
  service_id: string;
  service_name: string;
  unit_price_paise: number;
}

export interface UnlimitedRow {
  service_id: string;
  service_name: string;
}

export interface PoolRow {
  service_id: string;
  service_name: string;
  unit_price_paise: number;
}

export type PackageBlock =
  | { id: string; kind: "items"; bonus: boolean; rows: ItemsRow[] }
  | {
      id: string;
      kind: "choice";
      bonus: boolean;
      picks: string;
      choose_at: ChooseAt;
      rows: ChoiceRow[];
    }
  | {
      id: string;
      kind: "unlimited";
      bonus: boolean;
      assigned_value_paise: number;
      daily_cap: string; // "" = no cap
      rows: UnlimitedRow[];
    }
  | { id: string; kind: "pool"; bonus: boolean; sessions: string; rows: PoolRow[] }
  | {
      id: string;
      kind: "credit";
      bonus: boolean;
      amount_paise: number;
      scope: CreditScope;
    };

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
  // Items carry gross prices; discount.value is paise for flat/final, % for pct
  discount: { mode: DiscountMode; value: string } | null;
  final_price_paise: number;
  // v2 entitlement-block stack; null for v1 (items-based) packages.
  blocks: PackageBlock[] | null;
  created_at: string;
  updated_at: string;
}

// Payload the v2 block builder sends to create/update a definition. Mirrors the
// loosened backend schema: blocks + builder-computed price, no items envelope.
export interface PackageDefinitionV2Payload {
  name: string;
  description?: string;
  validity_days: number;
  cancellation_fee_pct: string;
  shareability: Shareability;
  auto_apply: boolean;
  blocks: PackageBlock[];
  final_price_paise: number;
  discount?: { mode: DiscountMode; value: string };
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
  pool_exempt: boolean;
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
  blocks_snapshot: PackageBlock[] | null;
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
  /** How many more times this service can be redeemed from this package. */
  remaining_uses: number;
  /** This service's own per-line cap (independent of other services). */
  line_remaining: number;
  /** Key of a budget shared across services (global pool / block); null = none. */
  shared_budget_key: string | null;
  /** Remaining units in the shared budget. */
  shared_remaining: number;
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
