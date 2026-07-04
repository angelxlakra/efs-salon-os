---
name: zustand-store
description: "Create or update Zustand stores following Aasan conventions. Use when adding new state management, store actions, or computed values."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Zustand Store Conventions

Aasan uses Zustand for client-side state management. All stores live in `frontend/src/stores/` and follow consistent patterns.

## Existing Stores

| Store | File | Purpose | Persistence |
|-------|------|---------|-------------|
| `useCartStore` | `cart-store.ts` | POS cart items, discounts, session | None (ephemeral) |
| `useAuthStore` | `auth-store.ts` | User, login/logout, permissions | `zustand/persist` → localStorage |
| `useSettingsStore` | `settings-store.ts` | Salon config, GST settings | None (fetched on mount) |

## Store Structure Pattern

```typescript
import { create } from 'zustand';
import { apiClient } from '@/lib/api-client';

// 1. Define the data interface
interface MyData {
  id: string;
  name: string;
  amount: number; // always paise (integer)
}

// 2. Define store interface: state + actions + computed
interface MyStore {
  // State
  items: MyData[];
  isLoading: boolean;

  // Actions (mutate state)
  fetchItems: () => Promise<void>;
  addItem: (item: MyData) => void;
  removeItem: (id: string) => void;

  // Computed (derived values via get())
  getTotal: () => number;
}

// 3. Create store
export const useMyStore = create<MyStore>((set, get) => ({
  items: [],
  isLoading: false,

  fetchItems: async () => {
    try {
      set({ isLoading: true });
      const { data } = await apiClient.get<MyData[]>('/my-resource');
      set({ items: data, isLoading: false });
    } catch (error) {
      console.error('Error fetching items:', error);
      set({ isLoading: false });
    }
  },

  addItem: (item) => {
    set({ items: [...get().items, item] });
  },

  removeItem: (id) => {
    set({ items: get().items.filter(item => item.id !== id) });
  },

  getTotal: () => {
    return get().items.reduce((sum, item) => sum + item.amount, 0);
  },
}));
```

## Key Conventions

### Money
- All amounts are **integers in paise** inside the store.
- Convert to rupees only at the display layer: `(amount / 100).toFixed(2)`.
- Use `Math.round()` for any arithmetic to avoid floating-point drift.

### IDs
- All IDs are **ULID strings** (26 chars, sortable).
- Generate with `import { ulid } from 'ulid'`.

### Persistence (when needed)
Use `zustand/persist` middleware for state that survives page refresh:

```typescript
import { persist } from 'zustand/middleware';

export const useMyStore = create<MyStore>()(
  persist(
    (set, get) => ({
      // ... store implementation
    }),
    {
      name: 'my-storage',          // localStorage key
      partialize: (state) => ({    // only persist these fields
        items: state.items,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
```

### API Integration
- Use `apiClient` from `@/lib/api-client` (Axios instance with auth interceptors).
- Always wrap async calls in try/catch with `isLoading` state.
- Backend returns `snake_case` — map to `camelCase` if needed (see auth-store login).

### Permission-Gated Actions
Check permissions before calling store actions in components:

```typescript
const { hasPermission } = useAuthStore();

// In component
{hasPermission('resource', 'action') && (
  <Button onClick={() => store.doAction()}>Action</Button>
)}
```

### Component Usage
```typescript
// Destructure what you need (Zustand auto-subscribes to used fields)
const { items, isLoading, fetchItems } = useMyStore();

// For computed values, call the function
const total = useMyStore().getTotal();

// Fetch on mount
useEffect(() => { fetchItems(); }, []);
```

## Anti-Patterns to Avoid

- Never store derived data — use computed functions via `get()`.
- Never store server state that should be fetched fresh (use React Query / SWR for that).
- Never put UI state (modal open/close, form values) in global stores.
- Never use `set()` with stale closures — always use `get()` for current state.
