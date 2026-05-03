import { apiClient } from "../api-client";

export type AppointmentStatus =
  | "scheduled"
  | "checked_in"
  | "in_progress"
  | "completed"
  | "cancelled";

export interface Appointment {
  id: string;
  ticket_number: string;
  visit_id: string | null;
  customer_id: string | null;
  customer_name: string;
  customer_phone: string | null;
  service_id: string;
  assigned_staff_id: string | null;
  scheduled_at: string;
  duration_minutes: number;
  status: AppointmentStatus;
  booking_notes: string | null;
  service_notes: string | null;
  checked_in_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppointmentCreate {
  customer_name: string;
  customer_phone: string;
  customer_id?: string;
  service_id: string;
  assigned_staff_id?: string;
  scheduled_at: string;
  duration_minutes: number;
  booking_notes?: string;
}

export interface AppointmentUpdate {
  service_id?: string;
  assigned_staff_id?: string;
  scheduled_at?: string;
  duration_minutes?: number;
  booking_notes?: string;
  service_notes?: string;
}

export interface StaffMember {
  id: string;
  display_name: string;
  specialization: string[] | null;
  is_active: boolean;
  is_service_provider: boolean;
}

export interface ServiceItem {
  id: string;
  name: string;
  base_price: number;
  duration_minutes: number;
  category_name: string;
}

export async function listAppointments(date: string): Promise<Appointment[]> {
  const { data } = await apiClient.get<Appointment[]>("/appointments", {
    params: { date },
  });
  return data;
}

export async function createAppointment(
  payload: AppointmentCreate
): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>("/appointments", payload);
  return data;
}

export async function updateAppointment(
  id: string,
  payload: AppointmentUpdate
): Promise<Appointment> {
  const { data } = await apiClient.patch<Appointment>(
    `/appointments/${id}`,
    payload
  );
  return data;
}

export async function cancelAppointment(id: string): Promise<void> {
  await apiClient.delete(`/appointments/${id}`);
}

export async function checkInAppointment(id: string): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>(
    `/appointments/${id}/check-in`
  );
  return data;
}

export async function startAppointment(id: string): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>(
    `/appointments/${id}/start`
  );
  return data;
}

export async function completeAppointment(id: string): Promise<Appointment> {
  const { data } = await apiClient.post<Appointment>(
    `/appointments/${id}/complete`
  );
  return data;
}

export async function listActiveStaff(): Promise<StaffMember[]> {
  const { data } = await apiClient.get<{ items: StaffMember[]; total: number }>(
    "/staff",
    { params: { is_active: true, is_service_provider: true, limit: 100 } }
  );
  return data.items;
}

export async function listServices(): Promise<ServiceItem[]> {
  const { data } = await apiClient.get<ServiceItem[]>("/catalog/services");
  return data;
}
