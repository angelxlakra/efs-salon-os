"use client";
import { useState } from "react";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { PackageBuilderEntitlementMatrix } from "./PackageBuilderEntitlementMatrix";
import { PackageBuilderServicesTable } from "./PackageBuilderServicesTable";
import { PackageBuilderDiscountControl } from "./PackageBuilderDiscountControl";
import { packagesApi } from "@/lib/api/packages";
import type {
  PackageDefinitionCreate,
  EntitlementType,
  Shareability,
  DiscountMode,
} from "@/types/package";

interface LineItem {
  service_id: string;
  service_name: string;
  quantity: number;
  unit_price_paise: number;
  locked: boolean;
  display_order: number;
  max_redemptions: number | null;
}

interface Props {
  initial?: PackageDefinitionCreate;
  onSaved: (id: string) => void;
}

export function PackageBuilder({ initial, onSaved }: Props) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [entitlementType, setEntitlementType] = useState<EntitlementType>(
    initial?.entitlement_type ?? "counted"
  );
  const [shareability, setShareability] = useState<Shareability>(
    initial?.shareability ?? "owner_only"
  );
  const [totalSessions, setTotalSessions] = useState<string>(
    String(initial?.total_sessions ?? "10")
  );
  const [validityDays, setValidityDays] = useState<string>(
    String(initial?.validity_days ?? "90")
  );
  const [cancellationFeePct, setCancellationFeePct] = useState<string>(
    initial?.cancellation_fee_pct ?? "20.00"
  );
  const [autoApply, setAutoApply] = useState<boolean>(
    initial?.auto_apply ?? true
  );
  const [items, setItems] = useState<LineItem[]>(
    (initial?.items ?? []).map((it, i) => ({
      service_id: it.service_id,
      service_name: "",
      quantity: it.quantity,
      unit_price_paise: it.unit_price_paise,
      locked: it.locked,
      display_order: it.display_order ?? i,
      max_redemptions: it.max_redemptions ?? null,
    }))
  );
  const [discount, setDiscount] = useState<
    { mode: DiscountMode; value: string } | undefined
  >(initial?.discount);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (!name.trim()) {
      toast.error("Package name is required");
      return;
    }
    if (items.length === 0) {
      toast.error("Add at least one service");
      return;
    }

    const payload: PackageDefinitionCreate = {
      name: name.trim(),
      description: description || undefined,
      entitlement_type: entitlementType,
      total_sessions:
        entitlementType === "counted"
          ? parseInt(totalSessions) || 10
          : undefined,
      shareability,
      validity_days: parseInt(validityDays) || 90,
      cancellation_fee_pct: cancellationFeePct,
      auto_apply: autoApply,
      items: items.map((it, i) => ({
        service_id: it.service_id || it.service_name, // fallback for manually-entered names
        quantity: entitlementType === "unlimited" ? 1 : it.quantity,
        unit_price_paise: it.unit_price_paise,
        locked: it.locked,
        display_order: i,
        max_redemptions: it.max_redemptions ?? null,
      })),
      discount,
    };

    setSaving(true);
    try {
      const res = await packagesApi.createDefinition(payload);
      toast.success("Package created");
      onSaved(res.data.id);
    } catch {
      toast.error("Failed to save package");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid grid-cols-[320px_1fr] gap-6 p-6">
      {/* Left: Package config */}
      <section className="space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="pkg-name">Package name</Label>
          <Input
            id="pkg-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Haircut Bundle × 10"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pkg-desc">Description (optional)</Label>
          <Textarea
            id="pkg-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What's included…"
            rows={2}
          />
        </div>

        <PackageBuilderEntitlementMatrix
          entitlementType={entitlementType}
          shareability={shareability}
          onChange={(et, sh) => {
            setEntitlementType(et);
            setShareability(sh);
          }}
        />

        {entitlementType === "counted" && (
          <div className="space-y-1.5">
            <Label htmlFor="pkg-sessions">Total sessions</Label>
            <Input
              id="pkg-sessions"
              type="number"
              min={1}
              value={totalSessions}
              onChange={(e) => setTotalSessions(e.target.value)}
            />
          </div>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="pkg-validity">Validity (days)</Label>
          <Input
            id="pkg-validity"
            type="number"
            min={1}
            value={validityDays}
            onChange={(e) => setValidityDays(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="pkg-fee">Cancellation fee (%)</Label>
          <Input
            id="pkg-fee"
            type="number"
            min={0}
            max={100}
            step="0.01"
            value={cancellationFeePct}
            onChange={(e) => setCancellationFeePct(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Auto-apply</p>
            <p className="text-xs text-muted-foreground">
              Automatically redeem when only one eligible package
            </p>
          </div>
          <Switch checked={autoApply} onCheckedChange={setAutoApply} />
        </div>
      </section>

      {/* Right: Services + pricing */}
      <section className="bg-card rounded-xl border border-border p-5 space-y-5">
        <PackageBuilderServicesTable
          items={items}
          onChange={setItems}
          entitlementType={entitlementType}
        />

        <PackageBuilderDiscountControl
          items={items}
          discount={discount}
          onChange={setDiscount}
        />

        <Button onClick={handleSave} disabled={saving} className="w-full">
          {saving && <Loader2 size={16} className="mr-2 animate-spin" />}
          Save &amp; draft
        </Button>
      </section>
    </div>
  );
}
