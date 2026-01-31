import { create } from 'zustand';
import { apiClient } from '@/lib/api-client';

interface SalonSettings {
  id: string;
  salon_name: string;
  salon_tagline: string | null;
  salon_address: string;
  salon_city: string | null;
  salon_state: string | null;
  salon_pincode: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  contact_website: string | null;
  gstin: string | null;
  pan: string | null;
  receipt_header_text: string | null;
  receipt_footer_text: string | null;
  receipt_show_gstin: boolean;
  receipt_show_logo: boolean;
  logo_url: string | null;
  primary_color: string | null;
  invoice_prefix: string;
  invoice_terms: string | null;
  created_at: string;
  updated_at: string;
}

interface SettingsStore {
  settings: SalonSettings | null;
  isLoading: boolean;
  hasGST: () => boolean;
  fetchSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: null,
  isLoading: false,

  hasGST: () => {
    const settings = get().settings;
    return !!(settings?.gstin && settings.gstin.trim().length > 0);
  },

  fetchSettings: async () => {
    try {
      set({ isLoading: true });
      const { data } = await apiClient.get<SalonSettings>('/settings');
      set({ settings: data, isLoading: false });
    } catch (error) {
      console.error('Error fetching settings:', error);
      set({ isLoading: false });
    }
  },
}));
