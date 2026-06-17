import {
  Calendar,
  Clock,
  CreditCard,
  FileText,
  Gift,
  Home,
  Package,
  Receipt,
  Scale,
  Settings as SettingsIcon,
  ShoppingCart,
  Tag,
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
  id: "today" | "people" | "catalogue" | "insight" | "admin";
  label: string;
  items: ShellNavItem[];
};

/** Sidebar nav grouped into 5 sections per brand roadmap §6.
 *  Single source of truth — sidebar + bottom-nav both read from here. */
export const SHELL_SECTIONS: ShellSection[] = [
  {
    id: "today",
    label: "Today",
    items: [
      { label: "Today", href: "/dashboard", icon: Home },
      { label: "POS", href: "/dashboard/pos", icon: ShoppingCart },
      { label: "Appointments", href: "/dashboard/appointments", icon: Calendar },
      { label: "Bills", href: "/dashboard/bills", icon: Receipt },
    ],
  },
  {
    id: "people",
    label: "People",
    items: [
      { label: "Customers", href: "/dashboard/customers", icon: Users },
      { label: "Attendance", href: "/dashboard/attendance", icon: Clock },
    ],
  },
  {
    id: "catalogue",
    label: "Catalogue",
    items: [
      { label: "Services", href: "/dashboard/services", icon: Tag },
      { label: "Inventory", href: "/dashboard/inventory", icon: Package },
      { label: "Packages", href: "/dashboard/packages", icon: Gift },
      { label: "Sold Packages", href: "/dashboard/packages/sold", icon: Receipt },
      { label: "Purchases", href: "/dashboard/purchases", icon: FileText },
    ],
  },
  {
    id: "insight",
    label: "Insight",
    items: [
      { label: "Reports", href: "/dashboard/reports", icon: TrendingUp },
      { label: "Expenses", href: "/dashboard/expenses", icon: Wallet },
      { label: "Cash Drawer", href: "/dashboard/cash-drawer", icon: CreditCard },
      { label: "Reconciliation", href: "/dashboard/reconciliation", icon: Scale },
    ],
  },
  {
    id: "admin",
    label: "Admin",
    items: [
      { label: "Users & Staff", href: "/dashboard/users", icon: UserCog },
      { label: "Settings", href: "/dashboard/settings", icon: SettingsIcon },
    ],
  },
];

/** Mobile bottom nav — 4 items per spec §3.3, "More" opens overflow sheet.
 *  Order reflects daily usage frequency for reception staff:
 *  Today → Appointments → POS → More.
 */
export const MOBILE_TABS: ShellNavItem[] = [
  { label: "Today", href: "/dashboard", icon: Home },
  { label: "Appointments", href: "/dashboard/appointments", icon: Calendar },
  { label: "POS", href: "/dashboard/pos", icon: ShoppingCart },
  // "More" tab is rendered specially in BottomTabNav — opens MoreSheet, not a route.
];

/** All nav hrefs across every section (for active-route resolution). */
export const ALL_NAV_HREFS: string[] = SHELL_SECTIONS.flatMap((s) =>
  s.items.map((i) => i.href),
);

/**
 * Resolve which single nav href is "active" for a pathname.
 *
 * Uses the LONGEST matching prefix so nested routes don't light up their
 * parent too — e.g. /dashboard/packages/sold activates "Sold Packages"
 * (/dashboard/packages/sold), not also "Packages" (/dashboard/packages).
 * Returns null when nothing matches.
 */
export function resolveActiveHref(
  pathname: string,
  hrefs: string[] = ALL_NAV_HREFS,
): string | null {
  if (pathname === "/dashboard") return "/dashboard";
  const matches = hrefs.filter(
    (h) => h !== "/dashboard" && (pathname === h || pathname.startsWith(h + "/")),
  );
  if (matches.length === 0) return null;
  return matches.reduce((best, h) => (h.length > best.length ? h : best));
}
