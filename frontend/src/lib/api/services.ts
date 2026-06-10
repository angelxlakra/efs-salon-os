// frontend/src/lib/api/services.ts
import { apiClient } from "@/lib/api-client";
import type { Service } from "@/types/service";

export async function fetchServicesList(): Promise<Service[]> {
  const response = await apiClient.get<Service[]>("/catalog/services");
  return response.data;
}
