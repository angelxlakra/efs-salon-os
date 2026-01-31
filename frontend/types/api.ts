// Base API types for SalonOS
export type Role = 'owner' | 'receptionist' | 'staff';

export interface User {
  id: string;
  username: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

// API Error types
export interface APIError {
  detail: string;
  status?: number;
}

// Permission helpers
export const PERMISSIONS = {
  canCreateBills: (role: Role) => ['owner', 'receptionist'].includes(role),
  canApplyDiscounts: (role: Role, amount?: number) => {
    if (role === 'owner') return true;
    if (role === 'receptionist' && amount && amount <= 50000) return true; // ₹500 = 50000 paise
    return false;
  },
  canRefundBills: (role: Role) => role === 'owner',
  canViewProfit: (role: Role) => role === 'owner',
  canApproveInventory: (role: Role) => role === 'owner',
  canViewSchedules: (role: Role) => true,
  canMarkComplete: (role: Role) => true,
  canExportReports: (role: Role) => ['owner', 'receptionist'].includes(role),
} as const;
