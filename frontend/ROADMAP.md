# SalonOS Frontend Development Roadmap

**Current Status**: Phase 1 - Foundation Complete ✅
**Next Phase**: Phase 2 - Core Features

---

## ✅ Phase 1: Foundation (COMPLETED)

### Infrastructure
- [x] Next.js 16 + React 19 setup
- [x] Tailwind CSS v4 configuration
- [x] TypeScript strict mode
- [x] Docker integration
- [x] Nginx reverse proxy configuration

### Authentication System
- [x] Login page with modern UI
- [x] JWT token management (access + refresh)
- [x] Zustand state management with persistence
- [x] Protected route component
- [x] Automatic token refresh on 401
- [x] Session persistence across page reloads
- [x] Home route smart redirect

### UI Components
- [x] shadcn/ui component library setup
- [x] Sidebar navigation component
- [x] Dashboard layout
- [x] Loading states and spinners
- [x] Alert/Toast components

---

## 🚧 Phase 2: Core Features (CURRENT)

### 1. POS (Point of Sale) System
**Priority**: HIGH 🔴
**Estimated Time**: 3-4 days

#### Pages to Build:
- `/dashboard/pos` - Main POS interface
  - Service selection grid/list
  - Cart management
  - Customer search/quick add
  - Discount application
  - Tax calculation display
  - Payment processing

#### Components:
- `ServiceGrid.tsx` - Display available services
- `CartSidebar.tsx` - Shopping cart with items
- `CustomerSelect.tsx` - Search and select customer
- `PaymentModal.tsx` - Payment method selection
- `ReceiptPreview.tsx` - Receipt preview before printing
- `QuickServiceAdd.tsx` - Quick add custom service/item

#### API Integration:
- `GET /api/pos/services` - Fetch available services
- `POST /api/pos/bills` - Create new bill
- `POST /api/pos/bills/:id/payments` - Process payment
- `GET /api/pos/bills/:id/receipt` - Get receipt data
- `POST /api/pos/bills/:id/print` - Trigger 80mm printer

#### Features:
- Real-time price calculation with GST
- Multiple payment methods (Cash, Card, UPI)
- Split payments
- Discount validation based on role
- Hot keys for quick actions (F1-F12)
- Receipt printing (80mm thermal)
- Bill history search

#### UI/UX Considerations:
- Large touch-friendly buttons
- Keyboard shortcuts for speed
- Clear visual feedback
- Price always visible
- One-click common actions

---

### 2. Appointments System
**Priority**: HIGH 🔴
**Estimated Time**: 4-5 days

#### Pages to Build:
- `/dashboard/appointments` - Calendar view
- `/dashboard/appointments/new` - Create appointment
- `/dashboard/appointments/:id` - Appointment details
- `/dashboard/walk-ins` - Walk-in registration

#### Components:
- `AppointmentCalendar.tsx` - Week/Day view calendar
- `AppointmentForm.tsx` - Create/edit appointment
- `TimeSlotPicker.tsx` - Available time slots
- `StaffSelector.tsx` - Select service provider
- `AppointmentCard.tsx` - Appointment card in list
- `ConflictDetector.tsx` - Show scheduling conflicts
- `WalkInForm.tsx` - Quick walk-in registration

#### API Integration:
- `GET /api/appointments` - List appointments (with filters)
- `POST /api/appointments` - Create appointment
- `PUT /api/appointments/:id` - Update appointment
- `DELETE /api/appointments/:id` - Cancel appointment
- `POST /api/appointments/:id/complete` - Mark complete
- `POST /api/appointments/:id/no-show` - Mark no-show
- `POST /api/walk-ins` - Register walk-in

#### Features:
- Daily/weekly/monthly calendar views
- Drag-and-drop rescheduling
- Staff availability display
- Color-coded by status (scheduled, completed, cancelled)
- Conflict detection and warnings
- Customer history on appointment
- SMS/WhatsApp reminders (future)
- Walk-in quick registration
- No-show tracking

#### UI/UX Considerations:
- Touch-friendly calendar
- Quick actions on hover/long-press
- Visual conflict indicators
- Staff workload visualization
- Time zone handling

---

### 3. Customer Management
**Priority**: MEDIUM 🟡
**Estimated Time**: 2-3 days

#### Pages to Build:
- `/dashboard/customers` - Customer list
- `/dashboard/customers/new` - Add customer
- `/dashboard/customers/:id` - Customer profile
- `/dashboard/customers/:id/history` - Visit history

#### Components:
- `CustomerList.tsx` - Searchable customer table
- `CustomerForm.tsx` - Create/edit customer
- `CustomerProfile.tsx` - Customer details
- `VisitHistory.tsx` - Past appointments and bills
- `CustomerStats.tsx` - Customer metrics (LTV, visits)
- `LoyaltyBadge.tsx` - Customer tier/loyalty status

#### API Integration:
- `GET /api/customers` - List customers
- `POST /api/customers` - Create customer
- `PUT /api/customers/:id` - Update customer
- `GET /api/customers/:id` - Customer details
- `GET /api/customers/:id/visits` - Visit history
- `GET /api/customers/:id/bills` - Billing history

#### Features:
- Advanced search and filters
- Customer visit history
- Total spent tracking
- Preferred services
- Notes and preferences
- Birthday tracking
- Loyalty/tier system
- Contact information (phone, email)
- Customer segmentation

---

### 4. Inventory Management
**Priority**: MEDIUM 🟡
**Estimated Time**: 3-4 days

#### Pages to Build:
- `/dashboard/inventory` - Product list
- `/dashboard/inventory/new` - Add SKU
- `/dashboard/inventory/:id` - Product details
- `/dashboard/inventory/requests` - Change requests
- `/dashboard/inventory/low-stock` - Low stock alerts

#### Components:
- `InventoryTable.tsx` - Product list with filters
- `SKUForm.tsx` - Create/edit SKU
- `StockChangeForm.tsx` - Request stock change
- `ApprovalQueue.tsx` - Pending approvals (owner)
- `LowStockAlert.tsx` - Low stock warnings
- `StockHistory.tsx` - Stock movement history
- `SupplierInfo.tsx` - Supplier details

#### API Integration:
- `GET /api/inventory/skus` - List products
- `POST /api/inventory/skus` - Create SKU
- `PUT /api/inventory/skus/:id` - Update SKU
- `POST /api/inventory/change-requests` - Stock change
- `GET /api/inventory/change-requests` - Pending requests
- `POST /api/inventory/change-requests/:id/approve` - Approve (owner)
- `GET /api/inventory/low-stock` - Low stock items

#### Features:
- SKU management
- Stock tracking
- Approval workflow (owner approval required)
- Low stock alerts
- Stock movement history
- Supplier information
- Barcode scanning (future)
- Reorder suggestions
- Cost tracking

---

## 📊 Phase 3: Reports & Analytics

### Priority: MEDIUM 🟡
**Estimated Time**: 3-4 days

#### Pages to Build:
- `/dashboard/reports` - Reports hub
- `/dashboard/reports/daily` - Daily summary
- `/dashboard/reports/monthly` - Monthly report
- `/dashboard/reports/tax` - GST reports
- `/dashboard/reports/staff` - Staff performance

#### Components:
- `ReportsHub.tsx` - Report selector
- `DailySummary.tsx` - Daily sales dashboard
- `MonthlyReport.tsx` - Monthly analytics
- `TaxReport.tsx` - GST breakdown
- `StaffPerformance.tsx` - Staff metrics
- `SalesChart.tsx` - Revenue charts
- `ServiceBreakdown.tsx` - Popular services
- `ExportButton.tsx` - Export to PDF/Excel

#### API Integration:
- `GET /api/reports/dashboard` - Real-time dashboard
- `GET /api/reports/daily` - Daily summaries
- `GET /api/reports/monthly` - Monthly report
- `GET /api/reports/tax` - GST report
- `GET /api/reports/staff/:id` - Staff performance
- `POST /api/reports/export` - Export report

#### Features:
- Real-time dashboard metrics
- Revenue charts (daily, weekly, monthly)
- Service popularity ranking
- Staff performance metrics
- Tax reports (CGST, SGST breakdown)
- Customer trends
- Peak hours analysis
- Export to PDF/Excel
- Date range filtering

---

## ⚙️ Phase 4: Settings & Configuration

### Priority: LOW 🟢
**Estimated Time**: 2-3 days

#### Pages to Build:
- `/dashboard/settings` - Settings hub
- `/dashboard/settings/profile` - User profile
- `/dashboard/settings/salon` - Salon info
- `/dashboard/settings/services` - Manage services
- `/dashboard/settings/users` - User management (owner)
- `/dashboard/settings/integrations` - Integrations

#### Components:
- `SettingsNav.tsx` - Settings navigation
- `ProfileForm.tsx` - Edit user profile
- `PasswordChange.tsx` - Change password
- `SalonInfoForm.tsx` - Edit salon details
- `ServiceCatalog.tsx` - Manage service catalog
- `UserManagement.tsx` - Create/edit users (owner)
- `RolePermissions.tsx` - View permissions

#### API Integration:
- `GET /api/auth/me` - Current user
- `POST /api/auth/change-password` - Change password
- `PUT /api/settings/salon` - Update salon info
- `GET /api/settings/services` - List services
- `POST /api/settings/services` - Create service
- `GET /api/users` - List users (owner)
- `POST /api/users` - Create user (owner)

#### Features:
- User profile editing
- Password change
- Salon information (name, address, GSTIN)
- Service catalog management
- User management (owner only)
- Role permissions display
- Printer configuration
- Backup settings
- Theme customization (future)

---

## 🔮 Phase 5: Advanced Features (Future)

### Customer Portal
- Self-service booking
- View appointment history
- Loyalty program
- Online payment

### WhatsApp Integration
- Appointment reminders
- Promotional campaigns
- Booking confirmations
- Payment links

### Analytics Dashboard
- Revenue forecasting
- Customer segmentation
- Marketing insights
- Churn prediction

### Staff Features
- Commission tracking
- Performance goals
- Personal schedules
- Tip management

### CCTV Integration
- Visitor analytics
- Security monitoring
- Occupancy tracking

---

## 📋 Development Priorities

### Immediate Next Steps (Week 1-2):
1. **POS System** - Most critical for daily operations
   - Start with service selection
   - Then cart management
   - Then payment processing
   - Finally receipt printing

2. **Appointments Calendar** - Core booking functionality
   - Week view first
   - Then day view with time slots
   - Add drag-and-drop
   - Conflict detection

### Medium Term (Week 3-4):
3. **Customer Management** - Customer relationship
4. **Inventory System** - Stock management
5. **Dashboard Improvements** - Better metrics

### Long Term (Month 2+):
6. **Reports & Analytics** - Business insights
7. **Settings & Config** - Customization
8. **Advanced Features** - Nice to have

---

## 🎨 Design System

### Colors (Already Configured)
- Primary: Salon brand color
- Secondary: Accent color
- Success: Green (#10b981)
- Warning: Yellow (#f59e0b)
- Error: Red (#ef4444)
- Gray scale for neutral elements

### Typography
- Headings: Bold, clear hierarchy
- Body: Readable, 16px base
- Small: 14px for secondary info

### Components to Maintain Consistency
- Buttons (Primary, Secondary, Ghost, Danger)
- Forms (Labels, Inputs, Validation)
- Cards (Elevated, Flat, Interactive)
- Tables (Sortable, Filterable, Responsive)
- Modals (Centered, Side drawer, Full screen)

---

## 🛠️ Technical Guidelines

### Code Structure
```
src/
├── app/
│   ├── (auth)/
│   │   └── login/
│   ├── dashboard/
│   │   ├── pos/
│   │   ├── appointments/
│   │   ├── customers/
│   │   ├── inventory/
│   │   ├── reports/
│   │   └── settings/
│   └── layout.tsx
├── components/
│   ├── ui/              # shadcn components
│   ├── pos/             # POS-specific
│   ├── appointments/    # Appointment-specific
│   └── shared/          # Reusable
├── lib/
│   ├── api-client.ts
│   ├── utils.ts
│   └── constants.ts
├── stores/
│   ├── auth-store.ts
│   ├── cart-store.ts    # POS cart
│   └── ui-store.ts      # UI state
├── types/
│   ├── api.ts
│   ├── auth.ts
│   ├── pos.ts
│   └── appointments.ts
└── hooks/
    ├── use-cart.ts
    ├── use-appointments.ts
    └── use-customers.ts
```

### Best Practices
1. **Component Size**: Keep components < 200 lines
2. **State Management**: Use Zustand for global, useState for local
3. **API Calls**: Use React Query for caching and invalidation
4. **Error Handling**: Always show user-friendly error messages
5. **Loading States**: Show skeleton loaders, not spinners
6. **Accessibility**: Support keyboard navigation
7. **Performance**: Use React.memo and useMemo judiciously
8. **Testing**: Write tests for critical flows

---

## 📦 Additional Dependencies Needed

### For POS System:
```bash
npm install @tanstack/react-query  # API caching
npm install date-fns               # Date utilities
npm install react-hot-toast        # Notifications (alternative to Sonner)
npm install zustand                # Already installed
```

### For Calendar:
```bash
npm install @fullcalendar/react
npm install @fullcalendar/daygrid
npm install @fullcalendar/timegrid
npm install @fullcalendar/interaction
```

### For Charts:
```bash
npm install recharts               # Charts for reports
npm install @tremor/react          # Dashboard components
```

### For Tables:
```bash
npm install @tanstack/react-table  # Powerful tables
```

### For Forms:
```bash
npm install react-hook-form        # Form management
npm install zod                    # Validation
npm install @hookform/resolvers    # Connect RHF + Zod
```

---

## 🧪 Testing Strategy

### Unit Tests
- Component rendering
- Utility functions
- Store actions

### Integration Tests
- API integration
- Form submission
- Navigation flows

### E2E Tests (Playwright)
- Login flow ✅
- POS checkout flow
- Appointment booking
- Payment processing

---

## 🚀 Deployment Checklist

Before going to production:
- [ ] Environment variables secured
- [ ] Error tracking (Sentry)
- [ ] Analytics (Plausible/Umami)
- [ ] Performance monitoring
- [ ] Database backups automated
- [ ] SSL certificate configured
- [ ] Domain configured (salon.local)
- [ ] Printer configured and tested
- [ ] User training completed
- [ ] Documentation finalized

---

**Last Updated**: January 19, 2026
**Status**: Phase 1 Complete, Starting Phase 2
