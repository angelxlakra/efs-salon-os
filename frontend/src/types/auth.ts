export interface User {
  id: string;
  username: string;
  fullName: string;
  email?: string;
  role: 'owner' | 'receptionist' | 'staff';
  permissions: Record<string, string[]>;
  lastLoginAt?: string;
  avatar_url?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
  deviceId?: string;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: string;
  expiresIn: number;
  user: User;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (resource: string, action: string) => boolean;
}
