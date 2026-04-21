# SalonOS Frontend

Modern, responsive frontend for SalonOS built with Next.js 16, React 19, and Tailwind CSS v4.

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **UI Library**: React 19
- **Styling**: Tailwind CSS v4 (CSS-first configuration)
- **Language**: TypeScript 5
- **API Client**: Custom fetch-based client with JWT authentication

## Getting Started

### Prerequisites

- Node.js 18+ (recommended: 20+)
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Copy environment file
cp .env.local.example .env.local

# Edit .env.local with your API URL
```

### Development

```bash
# Start dev server (runs on http://localhost:3000)
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint
```

## Project Structure

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with AuthProvider
│   ├── page.tsx           # Home page
│   ├── login/             # Login page
│   ├── dashboard/         # Protected dashboard
│   └── globals.css        # Global styles with Tailwind v4
├── components/            # Reusable React components
│   └── protected-route.tsx # Auth guard wrapper
├── lib/                   # Utility libraries
│   ├── api-client.ts      # API client for backend
│   └── auth-context.tsx   # Authentication context
├── types/                 # TypeScript type definitions
│   └── api.ts            # API types and permissions
├── next.config.ts        # Next.js configuration
├── tsconfig.json         # TypeScript configuration
└── postcss.config.mjs    # PostCSS config for Tailwind v4
```

## Features Implemented

### ✅ Phase 1 - Foundation

- [x] Next.js 16 with App Router
- [x] React 19 with TypeScript
- [x] Tailwind CSS v4 with custom theme
- [x] Authentication system with JWT
- [x] Protected routes
- [x] API client with error handling
- [x] Role-based permissions
- [x] Login page
- [x] Dashboard page with role-based UI

### 🚧 Phase 2 - Core Features (Next Steps)

- [ ] POS (Point of Sale) interface
- [ ] Appointments scheduling
- [ ] Inventory management
- [ ] Reports and analytics
- [ ] Settings and user management

## Tailwind CSS v4 Configuration

This project uses Tailwind CSS v4's new CSS-first configuration approach. Instead of `tailwind.config.js`, all customization is done directly in `app/globals.css` using the `@theme` directive:

```css
@theme {
  --color-primary: #6366f1;
  --color-success: #10b981;
  /* ... more custom properties */
}
```

### Custom Classes

- `.container-salon` - Responsive container with max-width
- `.card-salon` - Card component with shadow and border radius

### Print Styles

Receipt printing styles are included for 80mm thermal printers:

```css
@media print {
  .receipt-print { width: 80mm; }
  .no-print { display: none; }
}
```

## Authentication

The app uses JWT-based authentication with the following flow:

1. User submits credentials to `/api/auth/login`
2. Backend returns access token (15 min) and refresh token (7 days)
3. Tokens stored in localStorage
4. Access token sent in `Authorization: Bearer <token>` header
5. Protected routes check auth state via `useAuth()` hook

### Usage

```tsx
import { useAuth } from '@/lib/auth-context';

function MyComponent() {
  const { user, isAuthenticated, login, logout } = useAuth();

  // Check permissions
  if (user && PERMISSIONS.canCreateBills(user.role)) {
    // Show POS features
  }
}
```

## API Client

The API client provides typed methods for backend communication:

```tsx
import { apiClient } from '@/lib/api-client';

// GET request
const users = await apiClient.get<User[]>('/users');

// POST request
const bill = await apiClient.post('/pos/bills', billData);

// Automatic auth header injection
// Error handling with APIError type
```

## Environment Variables

### `.env.local`

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Production

Update `NEXT_PUBLIC_API_URL` to match your deployment:

```bash
NEXT_PUBLIC_API_URL=http://localhost/api
```

## Role-Based Permissions

Permissions are defined in `types/api.ts`:

```tsx
PERMISSIONS = {
  canCreateBills: (role) => ['owner', 'receptionist'].includes(role),
  canApplyDiscounts: (role, amount) => { /* ... */ },
  canRefundBills: (role) => role === 'owner',
  // ... more permissions
}
```

## Default Credentials

```
Username: owner
Password: change_me_123
```

⚠️ **Change immediately after first login!**

## TypeScript

Strict mode is enabled for better type safety. Path aliases are configured:

- `@/*` - Root directory
- `@/components/*` - Components directory
- `@/lib/*` - Lib directory
- `@/types/*` - Types directory
- `@/app/*` - App directory

## Docker Deployment

The frontend is configured for Docker deployment with `output: 'standalone'` in `next.config.ts`.

```dockerfile
FROM node:20-alpine AS base

# Install dependencies
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Build
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Production
FROM base AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
```

## Browser Support

- Chrome/Edge: Last 2 versions
- Firefox: Last 2 versions
- Safari: Last 2 versions

## Performance

- React strict mode enabled
- Automatic code splitting
- Image optimization with Next.js Image
- CSS optimization with Tailwind v4

## Contributing

1. Follow TypeScript best practices
2. Use functional components with hooks
3. Implement proper error handling
4. Add loading states for async operations
5. Ensure mobile responsiveness

## License

Proprietary - SalonOS
