// frontend/src/lib/api/packages.ts
import { apiClient } from "@/lib/api-client";
import type {
  PackageDefinition,
  PackageDefinitionCreate,
  PackageSale,
  PackageSaleSummary,
  EligiblePackage,
  RefundResponse,
} from "@/types/package";

export const packagesApi = {
  // ---- Catalog ----

  listDefinitions: (params?: { status?: string; search?: string }) =>
    apiClient.get<PackageDefinition[]>("/packages/definitions", { params }),

  getDefinition: (id: string) =>
    apiClient.get<PackageDefinition>(`/packages/definitions/${id}`),

  createDefinition: (payload: PackageDefinitionCreate) =>
    apiClient.post<PackageDefinition>("/packages/definitions", payload),

  updateDefinition: (id: string, payload: PackageDefinitionCreate) =>
    apiClient.put<PackageDefinition>(`/packages/definitions/${id}`, payload),

  publishDefinition: (id: string) =>
    apiClient.post<PackageDefinition>(`/packages/definitions/${id}/publish`),

  archiveDefinition: (id: string) =>
    apiClient.post<PackageDefinition>(`/packages/definitions/${id}/archive`),

  deleteDefinition: (id: string) =>
    apiClient.delete(`/packages/definitions/${id}`),

  // ---- Sales ----

  listSales: (params?: { customer_id?: string; status?: string }) =>
    apiClient.get<PackageSale[]>("/packages/sales", { params }),

  getSale: (id: string) =>
    apiClient.get<PackageSale>(`/packages/sales/${id}`),

  listActiveForCustomer: (customerId: string) =>
    apiClient.get<PackageSaleSummary[]>(
      `/packages/sales/active-for-customer/${customerId}`
    ),

  extendSale: (id: string, payload: { new_expires_at: string; reason: string }) =>
    apiClient.post<PackageSale>(`/packages/sales/${id}/extend`, payload),

  refundSale: (
    id: string,
    payload: { payment_method: string; reason: string }
  ) => apiClient.post<RefundResponse>(`/packages/sales/${id}/refund`, payload),

  // ---- Eligibility + undo ----

  checkEligibility: (payload: {
    customer_id: string;
    service_id: string;
  }) => apiClient.post<EligiblePackage[]>("/packages/eligibility/check", payload),

  undoRedemption: (auditId: string) =>
    apiClient.post(`/packages/redemptions/${auditId}/undo`),
};
