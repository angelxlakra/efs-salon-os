// frontend/src/stores/packages-store.ts
import { create } from "zustand";
import { packagesApi } from "@/lib/api/packages";
import type { PackageDefinition, PackageSaleSummary } from "@/types/package";

interface EligibilityEntry {
  packages: PackageSaleSummary[];
  loadedAt: number;
}

interface PackagesStore {
  // Catalog cache
  definitions: PackageDefinition[] | null;
  definitionsLoadedAt: number | null;
  loadDefinitions: (force?: boolean) => Promise<PackageDefinition[]>;

  // Per-customer eligibility cache
  eligibilityCache: Map<string, EligibilityEntry>;
  loadEligibility: (
    customerId: string,
    force?: boolean
  ) => Promise<PackageSaleSummary[]>;
  invalidateEligibility: (customerId: string) => void;
  invalidateAll: () => void;
}

const CATALOG_TTL_MS = 5 * 60 * 1000;   // 5 minutes
const ELIGIBILITY_TTL_MS = 60 * 1000;   // 60 seconds

export const usePackagesStore = create<PackagesStore>((set, get) => ({
  definitions: null,
  definitionsLoadedAt: null,

  async loadDefinitions(force = false) {
    const { definitions, definitionsLoadedAt } = get();
    const isFresh =
      definitionsLoadedAt != null &&
      Date.now() - definitionsLoadedAt < CATALOG_TTL_MS;

    if (definitions && isFresh && !force) return definitions;

    const res = await packagesApi.listDefinitions({ status: "published" });
    set({ definitions: res.data, definitionsLoadedAt: Date.now() });
    return res.data;
  },

  eligibilityCache: new Map(),

  async loadEligibility(customerId, force = false) {
    const cache = get().eligibilityCache;
    const entry = cache.get(customerId);
    const isFresh =
      entry != null && Date.now() - entry.loadedAt < ELIGIBILITY_TTL_MS;

    if (entry && isFresh && !force) return entry.packages;

    const res = await packagesApi.listActiveForCustomer(customerId);
    const updated = new Map(cache);
    updated.set(customerId, { packages: res.data, loadedAt: Date.now() });
    set({ eligibilityCache: updated });
    return res.data;
  },

  invalidateEligibility(customerId) {
    const updated = new Map(get().eligibilityCache);
    updated.delete(customerId);
    set({ eligibilityCache: updated });
  },

  invalidateAll() {
    set({
      definitions: null,
      definitionsLoadedAt: null,
      eligibilityCache: new Map(),
    });
  },
}));
