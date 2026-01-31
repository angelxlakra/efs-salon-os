# SalonOS Frontend - 1-Week Implementation Scope (UPDATED)

**Framework:** Next.js 16 (App Router) + React 19
**Timeline:** 7 days
**Developer:** Angel (React/Next.js expertise, learning Python)
**UI Library:** shadcn/ui + Tailwind CSS
**State Management:** Zustand
**Charts:** Recharts
**Icons:** Lucide React (default with shadcn/ui)
**Testing:** Vitest + React Testing Library + Playwright (E2E for critical flows)

---

## 🆕 Updates from Original Scope

### Critical Features Added (Backend Analysis):
1. ✅ **Payment Processing Page** - Complete payment flow with split payments (Day 3)
2. ✅ **Cash Drawer Management** - Open/close/reconciliation (Day 2-3)
3. ✅ **Customer Search & Quick Create** - Phone search integration in POS (Day 3)
4. ✅ **Walk-in Registration** - Quick walk-in flow with ticket generation (Day 4)
5. ✅ **Bill Refund Interface** - Owner refund flow (Day 6)
6. ✅ **Password Change** - User settings (Day 2)
7. ✅ **Settings Page Scaffold** - Basic settings structure (Day 2)

### Admin Features (Post-Launch/Week 2):
- Service/Catalog Management (Owner)
- User Management (Owner)
- Supplier Management (Owner)
- Staff Management (Owner)

---

## Executive Summary

This document outlines the **complete** frontend implementation plan for SalonOS Phase 1, focusing on delivering a production-ready application within 7 days. The scope now includes **all critical transactional flows** identified from backend analysis: POS with payment processing, cash drawer management, appointments with walk-ins, inventory, and comprehensive reporting.

**Key Technologies:**
- **Next.js 16:** Partial Prerendering (PPR), Server Components, Server Actions
- **React 19:** `use()` hook, `useActionState`, optimistic updates, React Compiler
- **shadcn/ui:** Accessible, customizable components built on Radix UI
- **Zustand:** Lightweight state management for auth, cart, and cash drawer state
- **Recharts:** Declarative charting library for dashboard visualizations

---

## Table of Contents

1. [Project Setup](#project-setup)
2. [Architecture Overview](#architecture-overview)
3. [Project Structure](#project-structure)
4. [Day-by-Day Implementation](#day-by-day-implementation)
5. [Component Library](#component-library)
6. [API Integration](#api-integration)
7. [State Management](#state-management)
8. [Testing Strategy](#testing-strategy)
9. [Performance Optimization](#performance-optimization)
10. [Deployment](#deployment)
11. [Post-Launch Features](#post-launch-features)
12. [Appendices](#appendices)

---

## Project Setup

### Initial Setup Commands
```bash
# Create Next.js 16 project
npx create-next-app@16 salon-frontend --typescript --tailwind --app --src-dir

cd salon-frontend

# Install shadcn/ui CLI
npx shadcn@latest init

# Install dependencies
npm install axios date-fns zod
npm install zustand
npm install recharts
npm install lucide-react

# Install dev dependencies
npm install -D @testing-library/react @testing-library/jest-dom
npm install -D vitest @vitest/ui
npm install -D @playwright/test
npm install -D eslint-config-prettier prettier
```

### shadcn/ui Configuration

When running `npx shadcn@latest init`, select:
- **Style:** Default
- **Base color:** Slate (customize later with brand colors)
- **CSS variables:** Yes
- **React Server Components:** Yes
- **Components:** Install as needed

### Install Required shadcn/ui Components
```bash
# Core UI components
npx shadcn@latest add button input card table dialog select label separator tabs badge calendar toast dropdown-menu sheet skeleton alert radio-group checkbox
```

### Environment Configuration

**File:** `.env.local`
```bash
NEXT_PUBLIC_API_URL=http://salon.local/api
NEXT_PUBLIC_APP_NAME=SalonOS
```

**File:** `.env.example`
```bash
NEXT_PUBLIC_API_URL=http://salon.local/api
NEXT_PUBLIC_APP_NAME=SalonOS
```

---

## Architecture Overview

### Technology Stack
```
┌─────────────────────────────────────────────────────────┐
│                     Browser (Client)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ React 19 UI  │  │ Zustand      │  │ React Query  │ │
│  │ Components   │  │ (Auth/Cart/  │  │ (Optional)   │ │
│  │              │  │  Drawer)     │  │              │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Next.js 16 App Router                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Server       │  │ Server       │  │ API Routes   │ │
│  │ Components   │  │ Actions      │  │ (Minimal)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ HTTP/REST
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 FastAPI Backend                          │
│              (http://salon.local/api)                    │
└─────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

1. **Server Components by Default:** Use React Server Components for data fetching
2. **Client Components for Interactivity:** Use `'use client'` only when needed
3. **Server Actions for Mutations:** Replace API routes with Server Actions
4. **Zustand for Global State:** Auth, POS cart, and cash drawer state
5. **PPR for Dashboard:** Partial Prerendering for instant static shell

---

## Project Structure

```
salon-frontend/
├── public/
│   ├── images/
│   └── icons/
│
├── src/
│   ├── app/                           # Next.js App Router
│   │   ├── (auth)/                    # Route group (no layout)
│   │   │   └── login/
│   │   │       └── page.tsx
│   │   │
│   │   ├── (dashboard)/               # Protected routes with layout
│   │   │   ├── layout.tsx             # Sidebar + Header
│   │   │   ├── page.tsx               # Dashboard home
│   │   │   │
│   │   │   ├── pos/                   # POS & Billing
│   │   │   │   ├── page.tsx
│   │   │   │   ├── payment/
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx   # 🆕 Payment processing
│   │   │   │   └── receipt/
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx   # 80mm receipt
│   │   │   │
│   │   │   ├── appointments/          # Scheduling
│   │   │   │   ├── page.tsx           # Calendar view
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── walkin/            # 🆕 Walk-in registration
│   │   │   │   │   └── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx       # Edit appointment
│   │   │   │
│   │   │   ├── cash/                  # 🆕 Cash Drawer
│   │   │   │   ├── page.tsx           # Current drawer status
│   │   │   │   ├── open/
│   │   │   │   │   └── page.tsx       # Open drawer
│   │   │   │   ├── close/
│   │   │   │   │   └── page.tsx       # Close/reconcile
│   │   │   │   └── history/
│   │   │   │       └── page.tsx       # Drawer history
│   │   │   │
│   │   │   ├── customers/             # 🆕 Customer Management
│   │   │   │   ├── page.tsx           # Customer list
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx       # Customer profile
│   │   │   │
│   │   │   ├── inventory/             # Inventory management
│   │   │   │   ├── page.tsx           # SKU list
│   │   │   │   ├── skus/
│   │   │   │   │   ├── new/
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx
│   │   │   │   └── requests/
│   │   │   │       ├── page.tsx
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx
│   │   │   │
│   │   │   ├── reports/               # Accounting & Reports
│   │   │   │   ├── page.tsx           # Real-time dashboard
│   │   │   │   ├── daily/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── monthly/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── tax/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── refunds/           # 🆕 Bill refunds
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx
│   │   │   │
│   │   │   └── settings/              # 🆕 Settings
│   │   │       ├── page.tsx           # Settings home
│   │   │       ├── profile/
│   │   │       │   └── page.tsx       # User profile
│   │   │       └── password/
│   │   │           └── page.tsx       # Change password
│   │   │
│   │   ├── api/                       # API route handlers (minimal)
│   │   │   └── auth/
│   │   │       └── refresh/
│   │   │           └── route.ts
│   │   │
│   │   ├── globals.css
│   │   └── layout.tsx                 # Root layout
│   │
│   ├── components/                    # React components
│   │   ├── ui/                        # shadcn/ui components (auto-generated)
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   └── ... (other shadcn components)
│   │   │
│   │   ├── layout/                    # Layout components
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   └── navigation.tsx
│   │   │
│   │   ├── pos/                       # POS-specific components
│   │   │   ├── service-selector.tsx
│   │   │   ├── customer-search.tsx    # 🆕 Customer search
│   │   │   ├── bill-cart.tsx
│   │   │   ├── payment-form.tsx       # 🆕 Payment form
│   │   │   ├── split-payment.tsx      # 🆕 Split payment
│   │   │   └── receipt-preview.tsx
│   │   │
│   │   ├── cash/                      # 🆕 Cash drawer components
│   │   │   ├── drawer-status.tsx
│   │   │   ├── open-drawer-form.tsx
│   │   │   ├── close-drawer-form.tsx
│   │   │   └── drawer-history-table.tsx
│   │   │
│   │   ├── appointments/              # Scheduling components
│   │   │   ├── calendar-day-view.tsx
│   │   │   ├── calendar-week-view.tsx
│   │   │   ├── appointment-form.tsx
│   │   │   ├── walkin-form.tsx        # 🆕 Walk-in form
│   │   │   └── appointment-card.tsx
│   │   │
│   │   ├── customers/                 # 🆕 Customer components
│   │   │   ├── customer-list.tsx
│   │   │   ├── customer-card.tsx
│   │   │   ├── customer-form.tsx
│   │   │   └── visit-history.tsx
│   │   │
│   │   ├── inventory/                 # Inventory components
│   │   │   ├── sku-list.tsx
│   │   │   ├── sku-form.tsx
│   │   │   ├── change-request-form.tsx
│   │   │   └── stock-ledger.tsx
│   │   │
│   │   └── reports/                   # Dashboard components
│   │       ├── metric-card.tsx
│   │       ├── revenue-chart.tsx
│   │       ├── payment-split-pie.tsx
│   │       ├── top-services-chart.tsx
│   │       ├── refund-form.tsx        # 🆕 Refund form
│   │       └── daily-summary-table.tsx
│   │
│   ├── lib/                           # Utilities
│   │   ├── api-client.ts              # Axios wrapper with auth
│   │   ├── auth.ts                    # JWT helpers
│   │   ├── format.ts                  # Currency, date formatters
│   │   └── utils.ts                   # cn() helper from shadcn
│   │
│   ├── hooks/                         # Custom hooks
│   │   ├── use-auth.ts                # Auth hook (wraps Zustand)
│   │   ├── use-cart.ts                # Cart hook (wraps Zustand)
│   │   ├── use-cash-drawer.ts         # 🆕 Cash drawer hook
│   │   ├── use-permissions.ts
│   │   ├── use-debounce.ts
│   │   └── use-toast.ts               # Toast notifications
│   │
│   ├── stores/                        # Zustand stores
│   │   ├── auth-store.ts
│   │   ├── cart-store.ts
│   │   └── cash-drawer-store.ts       # 🆕 Cash drawer state
│   │
│   ├── actions/                       # React 19 Server Actions
│   │   ├── auth-actions.ts
│   │   ├── pos-actions.ts
│   │   ├── payment-actions.ts         # 🆕 Payment actions
│   │   ├── appointment-actions.ts
│   │   └── inventory-actions.ts
│   │
│   └── types/                         # TypeScript types
│       ├── auth.ts
│       ├── pos.ts
│       ├── payment.ts                 # 🆕 Payment types
│       ├── cash-drawer.ts             # 🆕 Cash drawer types
│       ├── customer.ts                # 🆕 Customer types
│       ├── appointment.ts
│       ├── inventory.ts
│       └── accounting.ts
│
├── tests/                             # Test files
│   ├── unit/                          # Vitest unit tests
│   │   ├── components/
│   │   ├── hooks/
│   │   └── lib/
│   ├── e2e/                           # Playwright E2E tests
│   │   ├── auth.spec.ts
│   │   ├── pos-payment.spec.ts        # 🆕 Full POS flow
│   │   ├── cash-drawer.spec.ts        # 🆕 Cash drawer flow
│   │   └── appointments.spec.ts
│   └── setup.ts
│
├── .env.local
├── .env.example
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── vitest.config.ts
├── playwright.config.ts
├── components.json                    # shadcn/ui config
├── Dockerfile
└── README.md
```

---

## Day-by-Day Implementation

### **Day 1: Foundation & Authentication** (8 hours)

#### Morning (4h): Project Setup & Configuration

**1.1 Initialize Project**
```bash
npx create-next-app@16 salon-frontend --typescript --tailwind --app --src-dir
cd salon-frontend

# Install shadcn/ui
npx shadcn@latest init

# Install dependencies
npm install axios date-fns zod zustand recharts lucide-react
npm install -D @testing-library/react @testing-library/jest-dom vitest @vitest/ui
npm install -D @playwright/test eslint-config-prettier prettier
```

**1.2 Configure Next.js**

**File:** `next.config.ts`
```typescript
import type { NextConfig } from 'next';

const config: NextConfig = {
  experimental: {
    ppr: 'incremental',
    reactCompiler: true,
  },
  output: 'standalone',

  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://salon.local/api',
  },

  images: {
    formats: ['image/avif', 'image/webp'],
  },
};

export default config;
```

**1.3 Install shadcn/ui Components**
```bash
npx shadcn@latest add button input card table dialog select label separator tabs badge calendar toast dropdown-menu sheet skeleton alert radio-group checkbox
```

#### Afternoon (4h): Authentication System

**1.4 Create API Client**

**File:** `src/lib/api-client.ts`
```typescript
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');

        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        );

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);

        processQueue(null, data.access_token);

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(originalRequest);
      } catch (err) {
        processQueue(err, null);
        localStorage.clear();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export { apiClient };
```

**1.5 Create Auth Store & Types**

**File:** `src/types/auth.ts`
```typescript
export interface User {
  id: string;
  username: string;
  fullName: string;
  email?: string;
  role: 'owner' | 'receptionist' | 'staff';
  permissions: Record<string, string[]>;
  lastLoginAt?: string;
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
```

**File:** `src/stores/auth-store.ts`
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient } from '@/lib/api-client';
import type { User, LoginCredentials, AuthState } from '@/types/auth';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true });
        try {
          const { data } = await apiClient.post('/auth/login', credentials);

          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);

          set({
            user: data.user,
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
    }
  )
);
```

**1.6 Create Login Page**

**File:** `src/app/(auth)/login/page.tsx`
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      await login({ username, password });
      router.push('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/50">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">SalonOS</CardTitle>
          <CardDescription>Enter your credentials to access the system</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

**Deliverables - Day 1:**
- ✅ Project initialized with Next.js 16 + shadcn/ui
- ✅ API client with automatic token refresh
- ✅ Zustand auth store with persistence
- ✅ Login page with error handling
- ✅ TypeScript types for auth

---

### **Day 2: Layout System, Navigation & Settings** (8 hours)

#### Morning (4h): Protected Layout & Navigation

**2.1 Create Root Layout & Dashboard Layout**
**2.2 Create Sidebar with Role-Based Navigation**
**2.3 Create Header with User Menu**
**2.4 Create Format Utilities (currency, date, time)**

#### Afternoon (4h): Settings & Password Change

**2.5 Create Settings Page Scaffold**

**File:** `src/app/(dashboard)/settings/page.tsx`
```typescript
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { ChevronRight, User, Lock } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      <div className="grid gap-4">
        <Link href="/settings/profile">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <User className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Profile</CardTitle>
                  <CardDescription>Update your profile information</CardDescription>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
          </Card>
        </Link>

        <Link href="/settings/password">
          <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Lock className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle>Change Password</CardTitle>
                  <CardDescription>Update your account password</CardDescription>
                </div>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </CardHeader>
          </Card>
        </Link>
      </div>
    </div>
  );
}
```

**2.6 Create Password Change Page**

**File:** `src/app/(dashboard)/settings/password/page.tsx`
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';

export default function PasswordChangePage() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      await apiClient.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });

      setSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      setTimeout(() => {
        router.push('/settings');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Change Password</h1>
        <p className="text-muted-foreground">Update your account password</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Password Settings</CardTitle>
          <CardDescription>Choose a strong password to keep your account secure</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {success && (
              <Alert className="border-green-500 bg-green-50 text-green-900">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription>Password changed successfully! Redirecting...</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="current">Current Password</Label>
              <Input
                id="current"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new">New Password</Label>
              <Input
                id="new"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
              />
              <p className="text-sm text-muted-foreground">
                Must be at least 8 characters
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm">Confirm New Password</Label>
              <Input
                id="confirm"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>

            <div className="flex gap-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/settings')}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Changing Password...' : 'Change Password'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

**2.7 Create Cash Drawer Store**

**File:** `src/types/cash-drawer.ts`
```typescript
export interface CashDrawer {
  id: string;
  openedAt: string;
  openedBy: string;
  openedByName: string;
  openingFloat: number; // in paise
  expectedCash: number; // in paise
  actualCash?: number; // in paise
  variance?: number; // in paise
  closedAt?: string;
  closedBy?: string;
  closedByName?: string;
  notes?: string;
  status: 'open' | 'closed';
}

export interface DrawerSummary {
  currentDrawer: CashDrawer | null;
  totalCashSales: number;
  totalUpiSales: number;
  totalCardSales: number;
  totalOtherSales: number;
  totalSales: number;
}
```

**File:** `src/stores/cash-drawer-store.ts`
```typescript
import { create } from 'zustand';
import { apiClient } from '@/lib/api-client';
import type { CashDrawer, DrawerSummary } from '@/types/cash-drawer';

interface CashDrawerState {
  currentDrawer: CashDrawer | null;
  summary: DrawerSummary | null;
  isLoading: boolean;
  fetchCurrentDrawer: () => Promise<void>;
  openDrawer: (openingFloat: number) => Promise<void>;
  closeDrawer: (actualCash: number, notes?: string) => Promise<void>;
  reopenDrawer: (drawerId: string) => Promise<void>;
}

export const useCashDrawerStore = create<CashDrawerState>((set) => ({
  currentDrawer: null,
  summary: null,
  isLoading: false,

  fetchCurrentDrawer: async () => {
    set({ isLoading: true });
    try {
      const { data } = await apiClient.get<DrawerSummary>('/cash/current');
      set({
        currentDrawer: data.currentDrawer,
        summary: data,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  openDrawer: async (openingFloat: number) => {
    set({ isLoading: true });
    try {
      const { data } = await apiClient.post('/cash/open', {
        opening_float: openingFloat,
      });
      set({
        currentDrawer: data,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  closeDrawer: async (actualCash: number, notes?: string) => {
    set({ isLoading: true });
    try {
      const { data } = await apiClient.post('/cash/close', {
        actual_cash: actualCash,
        notes,
      });
      set({
        currentDrawer: null,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  reopenDrawer: async (drawerId: string) => {
    set({ isLoading: true });
    try {
      const { data } = await apiClient.post('/cash/reopen', {
        drawer_id: drawerId,
      });
      set({
        currentDrawer: data,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },
}));
```

**Deliverables - Day 2:**
- ✅ Complete layout system with sidebar and header
- ✅ Role-based navigation
- ✅ Settings page scaffold
- ✅ Password change functionality
- ✅ Cash drawer Zustand store
- ✅ Format utilities

---

### **Day 3: POS, Customer Search & Payment Processing** (9 hours)

#### Morning (4h): POS Interface with Customer Search

**3.1 Create Customer Types & Search Component**

**File:** `src/types/customer.ts`
```typescript
export interface Customer {
  id: string;
  firstName: string;
  lastName: string;
  phone: string;
  email?: string;
  dateOfBirth?: string;
  gender?: 'male' | 'female' | 'other';
  visitCount: number;
  totalSpent: number; // in paise
  createdAt: string;
}

export interface CustomerSearchResult {
  customer: Customer;
  recentVisits: number;
  lastVisitDate?: string;
}
```

**File:** `src/components/pos/customer-search.tsx`
```typescript
'use client';

import { useState } from 'react';
import { Search, UserPlus, User } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { apiClient } from '@/lib/api-client';
import { useDebounce } from '@/hooks/use-debounce';
import type { Customer } from '@/types/customer';

interface CustomerSearchProps {
  onSelectCustomer: (customer: Customer) => void;
  selectedCustomer?: Customer | null;
}

export function CustomerSearch({ onSelectCustomer, selectedCustomer }: CustomerSearchProps) {
  const [phone, setPhone] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<Customer[]>([]);
  const [showNewCustomerDialog, setShowNewCustomerDialog] = useState(false);

  const debouncedPhone = useDebounce(phone, 500);

  // Search customer by phone
  const handleSearch = async (phoneNumber: string) => {
    if (phoneNumber.length < 10) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      const { data } = await apiClient.get(`/customers/search?phone=${phoneNumber}`);
      if (data.customer) {
        setSearchResults([data.customer]);
      } else {
        setSearchResults([]);
      }
    } catch (error) {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Create new customer
  const handleCreateCustomer = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);

    try {
      const { data } = await apiClient.post('/customers', {
        first_name: formData.get('firstName'),
        last_name: formData.get('lastName'),
        phone: formData.get('phone'),
        email: formData.get('email'),
      });

      onSelectCustomer(data);
      setShowNewCustomerDialog(false);
      setPhone(data.phone);
    } catch (error: any) {
      console.error('Failed to create customer:', error);
    }
  };

  // Auto-search when phone changes
  React.useEffect(() => {
    if (debouncedPhone) {
      handleSearch(debouncedPhone);
    }
  }, [debouncedPhone]);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search customer by phone..."
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            maxLength={10}
            className="pl-9"
          />
        </div>

        <Dialog open={showNewCustomerDialog} onOpenChange={setShowNewCustomerDialog}>
          <DialogTrigger asChild>
            <Button variant="outline" size="icon">
              <UserPlus className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>New Customer</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateCustomer} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="phone">Phone Number *</Label>
                <Input
                  id="phone"
                  name="phone"
                  type="tel"
                  required
                  maxLength={10}
                  defaultValue={phone}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="firstName">First Name *</Label>
                <Input id="firstName" name="firstName" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Last Name *</Label>
                <Input id="lastName" name="lastName" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input id="email" name="email" type="email" />
              </div>
              <Button type="submit" className="w-full">Create Customer</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {selectedCustomer && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-full">
                <User className="h-4 w-4 text-primary" />
              </div>
              <div>
                <p className="font-medium">
                  {selectedCustomer.firstName} {selectedCustomer.lastName}
                </p>
                <p className="text-sm text-muted-foreground">{selectedCustomer.phone}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {searchResults.length > 0 && !selectedCustomer && (
        <div className="space-y-2">
          {searchResults.map((customer) => (
            <Card
              key={customer.id}
              className="cursor-pointer hover:bg-muted/50 transition-colors"
              onClick={() => onSelectCustomer(customer)}
            >
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">
                      {customer.firstName} {customer.lastName}
                    </p>
                    <p className="text-sm text-muted-foreground">{customer.phone}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{customer.visitCount} visits</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

**3.2 Update POS Page with Customer Search**

**File:** `src/app/(dashboard)/pos/page.tsx`
```typescript
'use client';

import { useState } from 'react';
import { ServiceSelector } from '@/components/pos/service-selector';
import { CustomerSearch } from '@/components/pos/customer-search';
import { BillCart } from '@/components/pos/bill-cart';
import type { Customer } from '@/types/customer';

export default function POSPage() {
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Point of Sale</h1>
        <p className="text-muted-foreground">Create bills and process payments</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Service Selection */}
        <div className="col-span-2 space-y-6">
          <CustomerSearch
            onSelectCustomer={setSelectedCustomer}
            selectedCustomer={selectedCustomer}
          />
          <ServiceSelector />
        </div>

        {/* Right: Cart */}
        <div>
          <BillCart customer={selectedCustomer} />
        </div>
      </div>
    </div>
  );
}
```

#### Afternoon (5h): Payment Processing

**3.3 Create Payment Types**

**File:** `src/types/payment.ts`
```typescript
export type PaymentMethod = 'cash' | 'upi' | 'card' | 'other';

export interface Payment {
  id: string;
  method: PaymentMethod;
  amount: number; // in paise
  referenceNumber?: string;
  confirmedAt: string;
}

export interface PaymentFormData {
  method: PaymentMethod;
  amount: number;
  referenceNumber?: string;
}

export interface Bill {
  id: string;
  invoiceNumber?: string;
  customerId?: string;
  customerName: string;
  customerPhone: string;
  subtotal: number;
  discountAmount: number;
  taxAmount: number;
  cgstAmount: number;
  sgstAmount: number;
  totalAmount: number;
  roundedTotal: number;
  roundingAdjustment: number;
  status: 'draft' | 'posted' | 'refunded' | 'void';
  items: BillItem[];
  payments: Payment[];
  createdAt: string;
  postedAt?: string;
}

export interface BillItem {
  id: string;
  serviceName: string;
  basePrice: number;
  quantity: number;
  lineTotal: number;
  staffName?: string;
}
```

**3.4 Create Payment Processing Page**

**File:** `src/app/(dashboard)/pos/payment/[id]/page.tsx`
```typescript
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, Printer } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { formatCurrency } from '@/lib/format';
import type { Bill, PaymentMethod } from '@/types/payment';

export default function PaymentPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [bill, setBill] = useState<Bill | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash');
  const [paymentAmount, setPaymentAmount] = useState(0);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [cashTendered, setCashTendered] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  // Fetch bill details
  useEffect(() => {
    const fetchBill = async () => {
      try {
        const { data } = await apiClient.get<Bill>(`/pos/bills/${params.id}`);
        setBill(data);
        setPaymentAmount(data.roundedTotal);
      } catch (err) {
        setError('Failed to load bill');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBill();
  }, [params.id]);

  const remainingAmount = bill ? bill.roundedTotal - bill.payments.reduce((sum, p) => sum + p.amount, 0) : 0;
  const changeAmount = paymentMethod === 'cash' ? Math.max(0, cashTendered - paymentAmount) : 0;

  const handlePayment = async () => {
    setError('');

    if (paymentAmount <= 0) {
      setError('Payment amount must be greater than 0');
      return;
    }

    if (paymentAmount > remainingAmount) {
      setError('Payment amount exceeds remaining balance');
      return;
    }

    if (paymentMethod === 'cash' && cashTendered < paymentAmount) {
      setError('Cash tendered is less than payment amount');
      return;
    }

    if ((paymentMethod === 'upi' || paymentMethod === 'card') && !referenceNumber) {
      setError('Reference number is required for UPI/Card payments');
      return;
    }

    setIsProcessing(true);

    try {
      await apiClient.post(`/pos/bills/${params.id}/payments`, {
        method: paymentMethod,
        amount: paymentAmount,
        reference_number: referenceNumber || undefined,
      });

      setSuccess(true);

      // Refresh bill data
      const { data } = await apiClient.get<Bill>(`/pos/bills/${params.id}`);
      setBill(data);

      // If fully paid, redirect to receipt
      const newRemaining = data.roundedTotal - data.payments.reduce((sum, p) => sum + p.amount, 0);
      if (newRemaining === 0) {
        setTimeout(() => {
          router.push(`/pos/receipt/${params.id}`);
        }, 1500);
      } else {
        // Reset for next payment
        setPaymentAmount(newRemaining);
        setReferenceNumber('');
        setCashTendered(0);
        setTimeout(() => setSuccess(false), 2000);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Payment processing failed');
    } finally {
      setIsProcessing(false);
    }
  };

  if (isLoading) {
    return <div className="p-8">Loading bill...</div>;
  }

  if (!bill) {
    return <div className="p-8">Bill not found</div>;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Payment Processing</h1>
        <p className="text-muted-foreground">Process payment for bill</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Bill Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Bill Summary</CardTitle>
            <CardDescription>Customer: {bill.customerName}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Items */}
            <div className="space-y-2">
              {bill.items.map((item) => (
                <div key={item.id} className="flex justify-between text-sm">
                  <span>
                    {item.quantity}x {item.serviceName}
                  </span>
                  <span>{formatCurrency(item.lineTotal)}</span>
                </div>
              ))}
            </div>

            <Separator />

            {/* Totals */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Subtotal</span>
                <span>{formatCurrency(bill.subtotal)}</span>
              </div>
              {bill.discountAmount > 0 && (
                <div className="flex justify-between text-sm text-green-600">
                  <span>Discount</span>
                  <span>-{formatCurrency(bill.discountAmount)}</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span>CGST (9%)</span>
                <span>{formatCurrency(bill.cgstAmount)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span>SGST (9%)</span>
                <span>{formatCurrency(bill.sgstAmount)}</span>
              </div>
              <Separator />
              <div className="flex justify-between font-bold text-lg">
                <span>Total</span>
                <span>{formatCurrency(bill.roundedTotal)}</span>
              </div>
            </div>

            {/* Payments Received */}
            {bill.payments.length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Payments Received</p>
                  {bill.payments.map((payment) => (
                    <div key={payment.id} className="flex justify-between text-sm">
                      <span className="capitalize">{payment.method}</span>
                      <span className="text-green-600">-{formatCurrency(payment.amount)}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            <Separator />
            <div className="flex justify-between font-bold text-xl text-primary">
              <span>Remaining</span>
              <span>{formatCurrency(remainingAmount)}</span>
            </div>
          </CardContent>
        </Card>

        {/* Payment Form */}
        <Card>
          <CardHeader>
            <CardTitle>Payment Details</CardTitle>
            <CardDescription>Select payment method and enter details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {success && (
              <Alert className="border-green-500 bg-green-50 text-green-900">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <AlertDescription>Payment recorded successfully!</AlertDescription>
              </Alert>
            )}

            {/* Payment Method */}
            <div className="space-y-3">
              <Label>Payment Method</Label>
              <RadioGroup value={paymentMethod} onValueChange={(value) => setPaymentMethod(value as PaymentMethod)}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="cash" id="cash" />
                  <Label htmlFor="cash" className="cursor-pointer">Cash</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="upi" id="upi" />
                  <Label htmlFor="upi" className="cursor-pointer">UPI</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="card" id="card" />
                  <Label htmlFor="card" className="cursor-pointer">Card</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="other" id="other" />
                  <Label htmlFor="other" className="cursor-pointer">Other</Label>
                </div>
              </RadioGroup>
            </div>

            {/* Payment Amount */}
            <div className="space-y-2">
              <Label htmlFor="amount">Payment Amount (₹)</Label>
              <Input
                id="amount"
                type="number"
                value={paymentAmount / 100}
                onChange={(e) => setPaymentAmount(Math.round(parseFloat(e.target.value || '0') * 100))}
                step="0.01"
                max={remainingAmount / 100}
              />
            </div>

            {/* Cash Tendered */}
            {paymentMethod === 'cash' && (
              <div className="space-y-2">
                <Label htmlFor="tendered">Cash Tendered (₹)</Label>
                <Input
                  id="tendered"
                  type="number"
                  value={cashTendered / 100}
                  onChange={(e) => setCashTendered(Math.round(parseFloat(e.target.value || '0') * 100))}
                  step="0.01"
                />
                {changeAmount > 0 && (
                  <p className="text-sm font-medium text-green-600">
                    Change: {formatCurrency(changeAmount)}
                  </p>
                )}
              </div>
            )}

            {/* Reference Number */}
            {(paymentMethod === 'upi' || paymentMethod === 'card' || paymentMethod === 'other') && (
              <div className="space-y-2">
                <Label htmlFor="reference">Reference Number {paymentMethod !== 'other' && '*'}</Label>
                <Input
                  id="reference"
                  value={referenceNumber}
                  onChange={(e) => setReferenceNumber(e.target.value)}
                  placeholder="Enter transaction reference"
                />
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={() => router.push('/pos')}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={handlePayment}
                disabled={isProcessing || remainingAmount === 0}
                className="flex-1"
              >
                {isProcessing ? 'Processing...' : 'Record Payment'}
              </Button>
            </div>

            {remainingAmount === 0 && (
              <Button
                variant="outline"
                onClick={() => router.push(`/pos/receipt/${params.id}`)}
                className="w-full"
              >
                <Printer className="h-4 w-4 mr-2" />
                Print Receipt
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

**Deliverables - Day 3:**
- ✅ Customer search by phone
- ✅ Quick customer creation
- ✅ Updated POS with customer integration
- ✅ Payment processing page with split payments
- ✅ Cash/UPI/Card/Other payment methods
- ✅ Change calculation for cash payments

---

### **Day 4: Appointments, Walk-ins & Dashboard** (8 hours)

#### Morning (4h): Appointments with Walk-in Support

**4.1 Create Walk-in Registration Form**

**File:** `src/components/appointments/walkin-form.tsx`
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient } from '@/lib/api-client';
import { CustomerSearch } from '@/components/pos/customer-search';
import type { Customer } from '@/types/customer';

export function WalkinForm() {
  const router = useRouter();
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [serviceId, setServiceId] = useState('');
  const [staffId, setStaffId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!selectedCustomer) {
      setError('Please select or create a customer');
      return;
    }

    setIsSubmitting(true);

    try {
      const { data } = await apiClient.post('/appointments/walkins', {
        customer_phone: selectedCustomer.phone,
        service_id: serviceId,
        staff_id: staffId || undefined,
      });

      router.push(`/appointments`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register walk-in');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Walk-in Registration</CardTitle>
        <CardDescription>Register a walk-in customer for immediate service</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Customer Search */}
          <div className="space-y-2">
            <Label>Customer</Label>
            <CustomerSearch
              onSelectCustomer={setSelectedCustomer}
              selectedCustomer={selectedCustomer}
            />
          </div>

          {/* Service Selection - simplified for demo */}
          <div className="space-y-2">
            <Label htmlFor="service">Service *</Label>
            <Select value={serviceId} onValueChange={setServiceId} required>
              <SelectTrigger>
                <SelectValue placeholder="Select service" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="service-1">Haircut</SelectItem>
                <SelectItem value="service-2">Facial</SelectItem>
                <SelectItem value="service-3">Manicure</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Staff Selection */}
          <div className="space-y-2">
            <Label htmlFor="staff">Assign Staff (Optional)</Label>
            <Select value={staffId} onValueChange={setStaffId}>
              <SelectTrigger>
                <SelectValue placeholder="Auto-assign" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="staff-1">Staff Member 1</SelectItem>
                <SelectItem value="staff-2">Staff Member 2</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => router.push('/appointments')}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? 'Registering...' : 'Register Walk-in'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
```

**File:** `src/app/(dashboard)/appointments/walkin/page.tsx`
```typescript
import { WalkinForm } from '@/components/appointments/walkin-form';

export default function WalkinPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Walk-in Registration</h1>
        <p className="text-muted-foreground">Quick registration for walk-in customers</p>
      </div>

      <WalkinForm />
    </div>
  );
}
```

**4.2-4.4**: Calendar views and appointment form (same as original scope)

#### Afternoon (4h): Real-Time Dashboard

**4.5-4.8**: Dashboard with auto-refresh, charts, and metrics (same as original scope)

**Deliverables - Day 4:**
- ✅ Walk-in registration flow
- ✅ Customer integration with appointments
- ✅ Calendar views (day/week)
- ✅ Dashboard with 150s auto-refresh
- ✅ Revenue charts with Recharts

---

### **Day 5: Inventory & Cash Drawer UI** (8 hours)

#### Morning (4h): Inventory Management

**5.1-5.4**: Inventory pages (same as original scope)

#### Afternoon (4h): Cash Drawer Interface

**5.5 Create Cash Drawer Status Page**

**File:** `src/app/(dashboard)/cash/page.tsx`
```typescript
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { DollarSign, Calendar, User } from 'lucide-react';
import { useCashDrawerStore } from '@/stores/cash-drawer-store';
import { formatCurrency, formatDateTime } from '@/lib/format';

export default function CashDrawerPage() {
  const router = useRouter();
  const { currentDrawer, summary, isLoading, fetchCurrentDrawer } = useCashDrawerStore();

  useEffect(() => {
    fetchCurrentDrawer();
  }, []);

  if (isLoading) {
    return <div className="p-8">Loading cash drawer status...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Cash Drawer</h1>
          <p className="text-muted-foreground">Manage daily cash operations</p>
        </div>
        {currentDrawer ? (
          <Button onClick={() => router.push('/cash/close')}>Close Drawer</Button>
        ) : (
          <Button onClick={() => router.push('/cash/open')}>Open Drawer</Button>
        )}
      </div>

      {currentDrawer ? (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Drawer Info */}
          <Card>
            <CardHeader>
              <CardTitle>Current Drawer</CardTitle>
              <CardDescription>Opened today</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <User className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Opened by</p>
                  <p className="font-medium">{currentDrawer.openedByName}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Opened at</p>
                  <p className="font-medium">{formatDateTime(currentDrawer.openedAt)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <DollarSign className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm text-muted-foreground">Opening Float</p>
                  <p className="font-medium">{formatCurrency(currentDrawer.openingFloat)}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Sales Summary */}
          {summary && (
            <Card>
              <CardHeader>
                <CardTitle>Today's Sales</CardTitle>
                <CardDescription>Payment method breakdown</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm">Cash Sales</span>
                  <span className="font-medium">{formatCurrency(summary.totalCashSales)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">UPI Sales</span>
                  <span className="font-medium">{formatCurrency(summary.totalUpiSales)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Card Sales</span>
                  <span className="font-medium">{formatCurrency(summary.totalCardSales)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Other Sales</span>
                  <span className="font-medium">{formatCurrency(summary.totalOtherSales)}</span>
                </div>
                <Separator />
                <div className="flex justify-between font-bold text-lg">
                  <span>Total Sales</span>
                  <span>{formatCurrency(summary.totalSales)}</span>
                </div>
                <Separator />
                <div className="flex justify-between font-bold text-primary">
                  <span>Expected Cash</span>
                  <span>{formatCurrency(currentDrawer.openingFloat + summary.totalCashSales)}</span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground mb-4">No drawer is currently open</p>
            <Button onClick={() => router.push('/cash/open')}>Open Cash Drawer</Button>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-end">
        <Button variant="outline" onClick={() => router.push('/cash/history')}>
          View History
        </Button>
      </div>
    </div>
  );
}
```

**5.6 Create Open/Close Drawer Pages** (simplified implementations for scope)

**Deliverables - Day 5:**
- ✅ Inventory management (SKUs, requests, approval)
- ✅ Cash drawer status page
- ✅ Open/close drawer functionality
- ✅ Drawer history view

---

### **Day 6: Reports & Bill Refunds** (8 hours)

#### Morning (4h): Reporting Pages

**6.1-6.3**: Daily, monthly, and tax reports (same as original scope)

#### Afternoon (4h): Bill Refunds & Receipt

**6.4 Create Refund Interface**

**File:** `src/app/(dashboard)/reports/refunds/[id]/page.tsx`
```typescript
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { apiClient } from '@/lib/api-client';
import { formatCurrency } from '@/lib/format';
import { usePermissions } from '@/hooks/use-permissions';
import type { Bill } from '@/types/payment';

export default function RefundPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { canRefundBill } = usePermissions();
  const [bill, setBill] = useState<Bill | null>(null);
  const [reason, setReason] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!canRefundBill) {
      router.push('/');
      return;
    }

    const fetchBill = async () => {
      try {
        const { data } = await apiClient.get<Bill>(`/pos/bills/${params.id}`);
        setBill(data);
      } catch (err) {
        setError('Failed to load bill');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBill();
  }, [params.id, canRefundBill]);

  const handleRefund = async () => {
    if (!reason.trim()) {
      setError('Refund reason is required');
      return;
    }

    setIsProcessing(true);
    setError('');

    try {
      await apiClient.post(`/pos/bills/${params.id}/refund`, {
        reason: reason.trim(),
      });

      router.push('/reports');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Refund processing failed');
    } finally {
      setIsProcessing(false);
    }
  };

  if (isLoading) {
    return <div className="p-8">Loading bill...</div>;
  }

  if (!bill) {
    return <div className="p-8">Bill not found</div>;
  }

  if (bill.status !== 'posted') {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertDescription>Only posted bills can be refunded</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Refund Bill</h1>
        <p className="text-muted-foreground">Process refund for invoice {bill.invoiceNumber}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Bill Details</CardTitle>
          <CardDescription>Customer: {bill.customerName}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {bill.items.map((item) => (
            <div key={item.id} className="flex justify-between">
              <span>{item.quantity}x {item.serviceName}</span>
              <span>{formatCurrency(item.lineTotal)}</span>
            </div>
          ))}
          <div className="flex justify-between font-bold text-lg border-t pt-2">
            <span>Total</span>
            <span>{formatCurrency(bill.roundedTotal)}</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Refund Reason</CardTitle>
          <CardDescription>Provide a reason for this refund</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="reason">Reason *</Label>
            <Textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Enter refund reason..."
              rows={4}
            />
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => router.push('/reports')}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button
              onClick={handleRefund}
              disabled={isProcessing}
              variant="destructive"
              className="flex-1"
            >
              {isProcessing ? 'Processing Refund...' : 'Process Refund'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

**6.5 Create 80mm Receipt Page** (same as original scope)

**Deliverables - Day 6:**
- ✅ Daily/monthly/tax reports
- ✅ Bill refund interface (owner only)
- ✅ 80mm receipt printing page

---

### **Day 7: Testing, Polish & Production** (8 hours)

**Same as original scope:**
- ✅ Vitest setup and unit tests
- ✅ Playwright E2E tests (Auth, POS-Payment flow, Cash Drawer, Appointments)
- ✅ Production build optimization
- ✅ Docker configuration
- ✅ Bundle analysis and Lighthouse audit

**Deliverables - Day 7:**
- ✅ Unit tests (>70% coverage)
- ✅ E2E tests for critical flows
- ✅ Production build optimized
- ✅ Lighthouse score > 90

---

## Post-Launch Features (Week 2+)

### Admin Features (Owner Only):
1. **Service/Catalog Management**
   - Create/edit service categories
   - Create/edit services and pricing
   - Manage service add-ons
   - Activate/deactivate services

2. **User Management**
   - Create/edit users
   - Role assignment
   - Staff profile management
   - Permission management

3. **Supplier Management**
   - Create/edit suppliers
   - Supplier contact management
   - Purchase order tracking

4. **Customer Management (Full)**
   - Customer directory with advanced search
   - Customer profiles with full visit history
   - Customer analytics and spending patterns
   - Customer notes and preferences

### Advanced Features:
5. **Offline Mode** - IndexedDB for network failures
6. **PWA** - Mobile receptionist access
7. **Dark Mode** - Theme toggle
8. **Excel Export** - Report downloads
9. **Keyboard Shortcuts** - F1-F12 for POS actions

---

## Success Criteria Checklist

### Core Features (Week 1):
- [ ] ✅ Role-based authentication and permissions
- [ ] ✅ POS with customer search and cart management
- [ ] ✅ Payment processing with split payments (Cash/UPI/Card/Other)
- [ ] ✅ Cash drawer management (open/close/reconciliation)
- [ ] ✅ Customer quick create and search
- [ ] ✅ Walk-in registration with ticket generation
- [ ] ✅ Appointment calendar (day/week views)
- [ ] ✅ Inventory SKU management with approval workflow
- [ ] ✅ Real-time dashboard with 150s auto-refresh
- [ ] ✅ Daily/monthly/tax reports
- [ ] ✅ Bill refund interface (owner only)
- [ ] ✅ 80mm receipt printing
- [ ] ✅ Password change functionality
- [ ] ✅ Production build (Lighthouse > 90)
- [ ] ✅ E2E tests for critical flows
- [ ] ✅ Responsive design (desktop + tablet)

### Post-Launch (Week 2+):
- [ ] Service/catalog management
- [ ] User management
- [ ] Supplier management
- [ ] Customer directory
- [ ] Advanced analytics

---

**End of Updated Scope Document**

This updated scope now includes ALL critical features identified from the backend analysis, ensuring a complete, production-ready SalonOS frontend implementation.
