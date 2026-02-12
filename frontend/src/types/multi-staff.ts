/**
 * TypeScript types for multi-staff service contribution system
 */

export type ContributionSplitType = 'percentage' | 'fixed' | 'equal' | 'time_based' | 'hybrid';

export interface ServiceStaffTemplate {
  id: string;
  service_id: string;
  role_name: string;
  role_description?: string;
  sequence_order: number;
  contribution_type: string;
  default_contribution_percent?: number;
  default_contribution_fixed?: number;
  estimated_duration_minutes: number;
  is_required: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ServiceWithTemplates {
  id: string;
  category_id: string;
  name: string;
  description?: string;
  base_price: number;
  duration_minutes: number;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  staff_templates: ServiceStaffTemplate[];
  category?: {
    id: string;
    name: string;
  };
}

export interface StaffContributionCreate {
  staff_id: string;
  role_in_service: string;
  sequence_order: number;
  contribution_split_type: ContributionSplitType;
  contribution_percent?: number;
  contribution_fixed?: number;
  time_spent_minutes?: number;
  notes?: string;
}

export interface StaffContributionResponse {
  id: string;
  bill_item_id: string;
  staff_id: string;
  role_in_service: string;
  sequence_order: number;
  contribution_split_type: string;
  contribution_percent?: number;
  contribution_fixed?: number;
  contribution_amount: number;
  time_spent_minutes?: number;
  base_percent_component?: number;
  time_component?: number;
  skill_component?: number;
  notes?: string;
  created_at: string;
}

export interface BillItemWithContributions {
  id: string;
  service_id?: string;
  sku_id?: string;
  item_name: string;
  base_price: number;
  quantity: number;
  line_total: number;
  cogs_amount?: number;
  staff_id?: string;
  notes?: string;
  staff_contributions: StaffContributionResponse[];
}

export interface StaffAssignment {
  templateId: string;
  staffId: string;
  actualTimeMinutes?: number;
  notes?: string;
}
