import {
  Calendar,
  CreditCard,
  FileText,
  Home,
  Package,
  Receipt,
  Settings as SettingsIcon,
  ShoppingCart,
  TrendingUp,
  UserCog,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";

export type ShellNavItem = {
  label: string;
  href: string;
  icon: LucideIcon;
};

export type ShellSection = {
  id: "today" | "ledger" | "insight" | "admin";
  label: string;
  items: ShellNavItem[];
};

/** Sidebar groupings per design_system.md §6.3. Single source of truth — sidebar + bottom-nav both read from here. */
export const SHELL_SECTIONS: ShellSection[] = [
  {
    id: "today",
    label: "Today's work",
    items: [
      { label: "Today", href: "/dashboard", icon: Home },
      { label: "POS", href: "/dashboard/pos", icon: ShoppingCart },
      { label: "Bills", href: "/dashboard/bills", icon: Receipt },
      { label: "Appointments", href: "/dashboard/appointments", icon: Calendar },
    ],
  },
  {
    id: "ledger",
    label: "Ledger",
    items: [
      { label: "Customers", href: "/dashboard/customers", icon: Users },
      { label: "Inventory", href: "/dashboard/inventory", icon: Package },
      { label: "Purchases", href: "/dashboard/purchases", icon: FileText },
      { label: "Expenses", href: "/dashboard/expenses", icon: Wallet },
      { label: "Cash Drawer", href: "/dashboard/cash-drawer", icon: CreditCard },
      { label: "Reconciliation", href: "/dashboard/reconciliation", icon: TrendingUp },
    ],
  },
  {
    id: "insight",
    label: "Insight",
    items: [
      { label: "Reports", href: "/dashboard/reports", icon: TrendingUp },
      { label: "Attendance", href: "/dashboard/attendance", icon: Calendar },
    ],
  },
  {
    id: "admin",
    label: "Admin",
    items: [
      { label: "Users & Staff", href: "/dashboard/users", icon: UserCog },
      { label: "Services", href: "/dashboard/services", icon: SettingsIcon },
      { label: "Settings", href: "/dashboard/settings", icon: SettingsIcon },
    ],
  },
];

/** Mobile bottom nav — 4 items per spec §3.3, "More" opens overflow sheet.
 *  Order reflects daily usage frequency for reception staff:
 *  Today → Appointments (highest-frequency calendar view) → POS → More.
 *  Bills is accessible via More since it's consulted less often than the calendar.
 */
export const MOBILE_TABS: ShellNavItem[] = [
  { label: "Today", href: "/dashboard", icon: Home },
  { label: "Appointments", href: "/dashboard/appointments", icon: Calendar },
  { label: "POS", href: "/dashboard/pos", icon: ShoppingCart },
  // The "More" tab is rendered specially in BottomTabNav — it opens MoreSheet, not a route.
];
