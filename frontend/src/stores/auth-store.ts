import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/lib/api-client';
import type { User, LoginCredentials, AuthState } from '@/types/auth';

interface AuthStateInternal extends AuthState {
  _hasHydrated: boolean;
  setHasHydrated: (hasHydrated: boolean) => void;
}

export const useAuthStore = create<AuthStateInternal>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      _hasHydrated: false,

      setHasHydrated: (hasHydrated: boolean) => {
        set({ _hasHydrated: hasHydrated });
      },

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true });
        try {
          // Backend returns snake_case, map to camelCase
          const { data } = await apiClient.post('/auth/login', credentials);

          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);

          // Map backend user fields to frontend format
          const user: User = {
            id: data.user.id,
            username: data.user.username,
            fullName: data.user.full_name,
            role: data.user.role,
            permissions: data.user.permissions,
          };

          set({
            user,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error) {
          set({ isLoading: false });
          throw error;
        }
      },

      logout: async () => {
        try {
          await apiClient.post('/auth/logout');
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          localStorage.clear();
          set({
            user: null,
            isAuthenticated: false,
          });
        }
      },

      hasPermission: (resource: string, action: string) => {
        const { user } = get();
        if (!user?.permissions) return false;
        const resourcePerms = user.permissions[resource];
        return resourcePerms?.includes(action) ?? false;
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
