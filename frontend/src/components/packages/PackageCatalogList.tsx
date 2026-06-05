"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Archive } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import { packagesApi } from "@/lib/api/packages";
import { SessionsLeft } from "@/components/ui/SessionsLeft";
import type { PackageDefinition } from "@/types/package";

const STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger"> = {
  draft: "warning",
  published: "success",
  archived: "neutral",
};

export function PackageCatalogList() {
  const router = useRouter();
  const { hasPermission } = useAuthStore();
  const canCreate = hasPermission("packages", "create");
  const canUpdate = hasPermission("packages", "update");

  const [definitions, setDefinitions] = useState<PackageDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "draft" | "published" | "archived">("all");

  useEffect(() => {
    (async () => {
      try {
        const res = await packagesApi.listDefinitions();
        setDefinitions(res.data);
      } catch {
        toast.error("Failed to load packages");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const filtered =
    filter === "all" ? definitions : definitions.filter((d) => d.status === filter);

  async function handlePublish(id: string) {
    try {
      await packagesApi.publishDefinition(id);
      setDefinitions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: "published" as const } : d))
      );
      toast.success("Published");
    } catch {
      toast.error("Failed to publish");
    }
  }

  async function handleArchive(id: string) {
    try {
      await packagesApi.archiveDefinition(id);
      setDefinitions((prev) =>
        prev.map((d) => (d.id === id ? { ...d, status: "archived" as const } : d))
      );
      toast.success("Archived");
    } catch {
      toast.error("Failed to archive");
    }
  }

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-heading-lg font-display">Packages</h1>
        {canCreate && (
          <Button onClick={() => router.push("/dashboard/packages/new")}>
            <Plus size={16} className="mr-1" /> New package
          </Button>
        )}
      </div>

      {/* Filter chips */}
      <div className="flex gap-2">
        {(["all", "draft", "published", "archived"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-sm border capitalize transition-colors ${
              filter === f
                ? "bg-accent text-accent-foreground border-accent"
                : "border-border text-muted-foreground hover:border-border-strong"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : filtered.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No packages.{" "}
          {canCreate && (
            <Link href="/dashboard/packages/new" className="underline">
              Create one.
            </Link>
          )}
        </p>
      ) : (
        <div className="rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-row border-b border-border">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Name</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Type</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Sessions</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Validity</th>
                <th className="text-left px-4 py-2.5 font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((d) => (
                <tr
                  key={d.id}
                  className="border-b border-border-subtle last:border-0 hover:bg-surface-row-hover"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/dashboard/packages/${d.id}`}
                      className="font-medium hover:underline"
                    >
                      {d.name}
                    </Link>
                    {d.description && (
                      <p className="text-xs text-muted-foreground truncate max-w-xs">
                        {d.description}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 capitalize text-muted-foreground">
                    {d.entitlement_type === "counted" ? "Counted" : "Unlimited"}
                    {d.shareability === "shared" && " · Shared"}
                  </td>
                  <td className="px-4 py-3 tabular-nums">
                    <SessionsLeft remaining={d.total_sessions} total={d.total_sessions} />
                  </td>
                  <td className="px-4 py-3 tabular-nums text-muted-foreground">
                    {d.validity_days}d
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={STATUS_TONE[d.status] ?? "neutral"} size="sm">
                      {d.status}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2 justify-end">
                      {canUpdate && d.status === "draft" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handlePublish(d.id)}
                        >
                          Publish
                        </Button>
                      )}
                      {canUpdate && d.status === "published" && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleArchive(d.id)}
                        >
                          <Archive size={14} className="mr-1" /> Archive
                        </Button>
                      )}
                      {canUpdate && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/dashboard/packages/${d.id}/edit`)}
                        >
                          Edit
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
