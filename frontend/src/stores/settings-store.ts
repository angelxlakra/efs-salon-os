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
  gst_registered: boolean;
  gst_effective_from: string | null;
  invoice_prefix_service: string;
  invoice_prefix_product: string;
  default_service_sac_code: string | null;
  default_product_hsn_code: string | null;
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
  isGstMode: () => boolean;
  isSplitBilling: () => boolean;
  servicesTaxed: () => boolean;
  fetchSettings: () => Promise<void>;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: null,
  isLoading: false,

  hasGST: () => {
    const settings = get().settings;
    return !!(settings?.gstin && settings.gstin.trim().length > 0);
  },

  // Split-billing scheme: retail products on their own 18%-inclusive bill,
  // services on theirs. Active once a GST effective date is set (and reached),
  // independent of the GST-registered toggle (the date check mirrors the server).
  isSplitBilling: () => {
    const eff = get().settings?.gst_effective_from;
    if (!eff) return false;
    return new Date().toISOString().slice(0, 10) >= eff;
  },

  // Whether services carry 5% GST (salon is GST-registered).
  servicesTaxed: () => !!get().settings?.gst_registered,

  // Back-compat alias: "GST mode" now means the split-billing scheme is active.
  isGstMode: () => {
    return get().isSplitBilling();
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
