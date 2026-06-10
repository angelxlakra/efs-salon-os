// frontend/src/lib/api/services.ts
import { apiClient } from "@/lib/api-client";
import type { ServiceItem } from "@/types/service";

export async function fetchServicesList(): Promise<ServiceItem[]> {
  const response = await apiClient.get<{
    services: Array<{
      id: string;
      name: string;
      base_price: number;
      duration_minutes: number;
      category: { id: string; name: string } | null;
    }>;
    total: number;
  }>("/catalog/services");
  return response.data.services.map((s) => ({
    id: s.id,
    name: s.name,
    base_price: s.base_price,
    duration_minutes: s.duration_minutes,
    category_name: s.category?.name ?? "Uncategorized",
  }));
}
