import { apiClient } from "../api-client";

export interface SalonSettings {
  id: string;
  salon_name: string;
  salon_tagline?: string;
  salon_address: string;
  salon_city?: string;
  salon_state?: string;
  salon_pincode?: string;
  contact_phone?: string;
  contact_email?: string;
  contact_website?: string;
  gstin?: string;
  pan?: string;
  receipt_header_text?: string;
  receipt_footer_text?: string;
  receipt_show_gstin: boolean;
  receipt_show_logo: boolean;
  logo_url?: string;
  primary_color?: string;
  invoice_prefix: string;
  invoice_terms?: string;
  created_at: string;
  updated_at: string;
}

export interface SalonSettingsUpdate {
  salon_name?: string;
  salon_tagline?: string;
  salon_address?: string;
  salon_city?: string;
  salon_state?: string;
  salon_pincode?: string;
  contact_phone?: string;
  contact_email?: string;
  contact_website?: string;
  gstin?: string;
  pan?: string;
  receipt_header_text?: string;
  receipt_footer_text?: string;
  receipt_show_gstin?: boolean;
  receipt_show_logo?: boolean;
  logo_url?: string;
  primary_color?: string;
  invoice_prefix?: string;
  invoice_terms?: string;
}

export const settingsApi = {
  getSettings: async (): Promise<SalonSettings> => {
    const response = await apiClient.get<SalonSettings>('/api/settings');
    return response.data;
  },

  updateSettings: async (updates: SalonSettingsUpdate): Promise<SalonSettings> => {
    const response = await apiClient.patch<SalonSettings>('/api/settings', updates);
    return response.data;
  },

  resetSettings: async (): Promise<SalonSettings> => {
    const response = await apiClient.post<SalonSettings>('/api/settings/reset');
    return response.data;
  },
};
