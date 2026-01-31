# Management System - Analysis & Implementation Plan

**Date**: January 19, 2026

---

## 📋 Role-Based Access Control (RBAC)

### Role Hierarchy:

#### 1. **OWNER** (Full Access) 👑
```json
{
  "billing": ["create", "read", "update", "refund", "discount", "view_totals"],
  "appointments": ["create", "read", "update", "delete", "assign_staff"],
  "inventory": ["create", "read", "update", "approve", "view_costs"],
  "accounting": ["view_dashboard", "view_profit", "export", "manage_drawer"],
  "users": ["create", "read", "update", "delete"],
  "settings": ["read", "update"],
  "schedule": ["view_all"],
  "services": ["mark_complete", "add_notes"]
}
```

**Special Permissions:**
- ✅ Unlimited discounts
- ✅ Approve inventory changes
- ✅ Manage users (create/edit/delete)
- ✅ View profit & financial data
- ✅ Refund bills
- ✅ Export reports
- ✅ Full PII access

---

#### 2. **RECEPTIONIST** (Front Desk) 💼
```json
{
  "billing": ["create", "read", "discount", "view_totals"],
  "appointments": ["create", "read", "update", "assign_staff"],
  "inventory": ["read", "request"],
  "accounting": ["view_dashboard", "manage_drawer"],
  "users": ["read"],
  "schedule": ["view_all"],
  "services": ["mark_complete", "add_notes"]
}
```

**Limitations:**
- ⚠️ Discounts up to ₹500 only
- ❌ Cannot refund bills
- ❌ Cannot delete appointments
- ❌ Cannot approve inventory
- ❌ Cannot manage users
- ✅ Full PII access

---

#### 3. **STAFF** (Service Providers) ✂️
```json
{
  "schedule": ["view_own", "view_all"],
  "services": ["mark_complete", "add_notes"]
}
```

**Limitations:**
- ❌ Cannot create bills
- ❌ Cannot view billing totals
- ❌ Limited customer PII (first name only)
- ❌ No phone/email access
- ✅ Can view their schedule
- ✅ Can mark services complete

---

## 🎯 Management Pages to Build

### 1. **Services Management** (`/dashboard/services`)

#### What is it?
Manage the service catalog - all treatments/services the salon offers.

#### Database Structure:
```typescript
ServiceCategory {
  id: string;
  name: string;              // "Haircut", "Hair Color", "Spa"
  description: string;
  display_order: number;     // For sorting
  is_active: boolean;
}

Service {
  id: string;
  category_id: string;
  name: string;              // "Men's Haircut", "Balayage"
  description: string;
  base_price: number;        // in paise
  duration_minutes: number;  // 30, 45, 60, etc.
  is_active: boolean;
  display_order: number;
}

ServiceAddon {
  id: string;
  service_id: string;
  name: string;              // "Hair wash", "Conditioning"
  price: number;             // in paise
}
```

#### Backend APIs Available:
- ✅ `GET /api/catalog/categories` - List categories
- ✅ `POST /api/catalog/categories` - Create category (Owner only)
- ✅ `PUT /api/catalog/categories/:id` - Update category (Owner only)
- ✅ `DELETE /api/catalog/categories/:id` - Delete category (Owner only)
- ✅ `GET /api/catalog/services` - List services
- ✅ `POST /api/catalog/services` - Create service (Owner only)
- ✅ `PUT /api/catalog/services/:id` - Update service (Owner only)
- ✅ `DELETE /api/catalog/services/:id` - Delete service (Owner only)
- ✅ `GET /api/catalog/full` - Get full catalog

#### Permission Requirements:
- **View**: All authenticated users
- **Create/Edit/Delete**: **Owner only**

#### Features to Build:
1. **Category Management**
   - List categories
   - Create new category
   - Edit category
   - Reorder categories (drag & drop)
   - Toggle active/inactive

2. **Service Management**
   - List services by category
   - Create new service
   - Edit service (name, price, duration, category)
   - Toggle active/inactive
   - Reorder services
   - Delete service (soft delete)

3. **Service Addons**
   - Add optional addons to services
   - Set addon prices
   - Manage addon list

---

### 2. **Users Management** (`/dashboard/users`)

#### What is it?
Manage salon staff accounts - owners, receptionists, and stylists.

#### Database Structure:
```typescript
Role {
  id: string;
  name: "owner" | "receptionist" | "staff";
  description: string;
  permissions: Record<string, string[]>;
}

User {
  id: string;
  role_id: string;
  username: string;
  email: string;
  password_hash: string;     // Never expose
  full_name: string;
  is_active: boolean;
  last_login_at: datetime;
  created_at: datetime;
}
```

#### Backend APIs:
- ⚠️ **MISSING** - Need to create `/api/users` endpoints
- Endpoints needed:
  - `GET /api/users` - List users
  - `POST /api/users` - Create user
  - `PUT /api/users/:id` - Update user
  - `DELETE /api/users/:id` - Delete/deactivate user
  - `POST /api/users/:id/reset-password` - Reset password

#### Permission Requirements:
- **View**: Owner only
- **Create/Edit/Delete**: **Owner only**
- **Note**: Users cannot edit themselves (security)

#### Features to Build:
1. **User List**
   - Table with: name, username, role, status, last login
   - Filter by role
   - Search by name

2. **Create User**
   - Form: username, email, full name, role, password
   - Password strength validation
   - Unique username check

3. **Edit User**
   - Update details (except password)
   - Change role
   - Toggle active/inactive

4. **Password Management**
   - Reset user password (Owner only)
   - Force password change on next login

---

### 3. **Customers Management** (`/dashboard/customers`)

#### What is it?
Customer database for tracking visits, preferences, and contact info.

#### Database Structure:
```typescript
Customer {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;             // Unique, encrypted
  email: string;             // Encrypted
  date_of_birth: date;
  gender: string;
  notes: string;             // Preferences, allergies
  total_visits: number;
  total_spent: number;       // in paise
  last_visit_at: datetime;
}
```

#### Backend APIs Available:
- ✅ `GET /api/customers` - List customers (paginated)
- ✅ `POST /api/customers` - Create customer
- ✅ `GET /api/customers/search?phone=...` - Search by phone
- ✅ `GET /api/customers/:id` - Get customer details
- ✅ `PUT /api/customers/:id` - Update customer
- ✅ `DELETE /api/customers/:id` - Delete customer (soft delete)

#### Permission Requirements:
- **View**: All authenticated users
- **Create/Edit**: Owner & Receptionist
- **Delete**: Owner only
- **PII Access**:
  - Owner & Receptionist: Full access
  - Staff: First name only, no phone/email

#### Features to Build:
1. **Customer List**
   - Searchable table
   - Filters: recent, top spenders, birthdays
   - Quick actions: view, edit, delete

2. **Customer Profile**
   - Contact details
   - Visit history
   - Total spent
   - Favorite services
   - Notes/preferences

3. **Add Customer**
   - Quick add form (minimal fields)
   - Full form (all details)
   - Duplicate phone detection

4. **Edit Customer**
   - Update contact info
   - Add notes
   - Track preferences

---

## 🔄 Ways to Add Customers

### Option 1: **Pre-Add Before Billing** ✅ RECOMMENDED
**When**: During appointment booking or before service
**Who**: Receptionist
**Flow**:
```
1. Customer walks in / calls
2. Receptionist creates customer record
   → Name, phone (required)
   → Email, DOB (optional)
3. Customer appears in database
4. During billing, search by phone
5. Select customer from list
6. Bill is linked to customer
```

**Pros**:
- Clean customer database
- Can track appointments
- Can send reminders
- Better analytics

**Cons**:
- Extra step before billing

---

### Option 2: **Quick Add During Billing** 🚀 FASTER
**When**: At POS during checkout
**Who**: Receptionist
**Flow**:
```
1. Add services to cart
2. Click "Add Customer" in cart sidebar
3. Enter phone number
4. If exists: Auto-select customer
5. If new: Quick form (name + phone)
6. Proceed to payment
7. Bill auto-links to customer
```

**Pros**:
- Fastest workflow
- No interruption to billing
- Captures walk-ins

**Cons**:
- Minimal data captured initially
- Need to edit later for full details

---

### Option 3: **Walk-in (No Customer)** 💨 SIMPLEST
**When**: Quick transactions
**Who**: Receptionist
**Flow**:
```
1. Add services to cart
2. Skip customer selection
3. Bill created as "Walk-in Customer"
4. No customer record linked
```

**Pros**:
- Fastest checkout
- No mandatory customer

**Cons**:
- No customer tracking
- No visit history
- Cannot send reminders

---

### Option 4: **Self-Registration (Future)** 📱
**When**: Before first visit
**Who**: Customer
**Flow**:
```
1. Customer scans QR code / visits link
2. Fills online form
3. Submits
4. Receptionist approves
5. Customer in database
6. Can book appointments online
```

**Pros**:
- Reduces receptionist work
- Customer provides accurate data
- Can integrate with booking portal

**Cons**:
- Requires separate portal
- Phase 5 feature

---

## 🏗️ Implementation Priority

### Phase 1: Services Management (Build First) ⭐
**Why First?**
- POS needs services to function
- Currently no services in database
- Blocking POS testing
- Owner-only, simpler permissions

**Pages:**
1. `/dashboard/services` - List view
2. `/dashboard/services/new` - Create service
3. `/dashboard/services/:id/edit` - Edit service
4. `/dashboard/services/categories` - Manage categories

**Time**: 2-3 days

---

### Phase 2: Customers Management ⭐⭐
**Why Second?**
- Needed for appointments
- Quick-add already in POS
- Enhance POS customer selection

**Pages:**
1. `/dashboard/customers` - List view
2. `/dashboard/customers/new` - Create customer
3. `/dashboard/customers/:id` - Profile view
4. `/dashboard/customers/:id/edit` - Edit customer

**Time**: 2-3 days

---

### Phase 3: Users Management ⭐⭐⭐
**Why Last?**
- Backend APIs need to be built first
- Owner-only feature
- Less urgent than services/customers
- Currently only 1 user (owner)

**Pages:**
1. `/dashboard/users` - List view
2. `/dashboard/users/new` - Create user
3. `/dashboard/users/:id/edit` - Edit user

**Backend Work Needed:**
- Create `/api/users` endpoints
- Implement user CRUD
- Add password reset

**Time**: 3-4 days (including backend)

---

## 🎨 UI Components Needed

### Shared Components:
1. **PermissionGuard.tsx**
   - Check user role before rendering
   - Show "Access Denied" for unauthorized users
   - Usage: `<PermissionGuard role="owner">...</PermissionGuard>`

2. **DataTable.tsx**
   - Sortable, filterable table
   - Pagination
   - Quick actions menu
   - Uses @tanstack/react-table

3. **FormDialog.tsx**
   - Modal form wrapper
   - Handles submit/cancel
   - Loading states

4. **ConfirmDialog.tsx**
   - Confirmation before delete
   - Destructive action warning

5. **SearchCombobox.tsx**
   - Searchable dropdown
   - For customer selection
   - Uses shadcn Command component

---

## 📦 Additional Dependencies Needed

```bash
# Table management
npm install @tanstack/react-table

# Form handling
npm install react-hook-form zod @hookform/resolvers

# Drag & drop (for reordering)
npm install @dnd-kit/core @dnd-kit/sortable
```

---

## 🔐 Security Considerations

### Frontend:
1. **Permission Checks**
   - Hide UI elements user can't access
   - Disable buttons based on role
   - Show read-only mode for staff

2. **PII Protection**
   - Mask phone numbers for staff
   - Hide email addresses for staff
   - Show "***-***-1234" format

3. **Validation**
   - Client-side for UX
   - Server-side for security
   - Never trust frontend data

### Backend:
1. **Authorization**
   - Verify permissions on every endpoint
   - Use `require_owner` dependency
   - Validate user can edit resource

2. **Audit Logging**
   - Log all CRUD operations
   - Track who changed what
   - Timestamp all actions

3. **Data Validation**
   - Validate all inputs
   - Sanitize user input
   - Prevent SQL injection

---

## 📊 Recommended Customer Flow

### For Your Salon:

**Scenario 1: New Customer (First Visit)**
```
1. Customer walks in
2. Receptionist: "First time here?"
3. Opens /dashboard/customers/new
4. Captures: Name, Phone, (optional: email, DOB)
5. Saves customer
6. Opens POS
7. Searches customer by phone
8. Adds services
9. Processes payment
```

**Scenario 2: Returning Customer**
```
1. Customer walks in
2. Opens POS
3. Searches customer by phone or name
4. Selects from list
5. Adds services
6. Processes payment
```

**Scenario 3: Walk-in (Quick)**
```
1. Customer walks in
2. Opens POS
3. Skips customer selection
4. Adds services
5. Processes payment
6. Bill saved as "Walk-in Customer"
```

**Best Practice**:
- Get phone number at minimum
- Enables future appointment reminders
- Builds customer database
- Receptionist can add details later

---

## 🚀 Next Steps

1. **Build Services Management First**
   - Create service categories (Haircut, Color, Spa, etc.)
   - Add services with prices
   - Test in POS

2. **Enhance POS Customer Selection**
   - Add searchable dropdown
   - Show customer history on selection
   - Quick add new customer button

3. **Build Customers Management**
   - Full CRUD interface
   - Customer profiles
   - Visit history

4. **Build Users Management**
   - Backend APIs first
   - Frontend CRUD interface
   - Password management

---

**Priority Order**: Services → Customers → Users

**Start With**: Services Management (blocks POS testing)

