'use client';

import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, CreditCard, Receipt, MoreHorizontal } from 'lucide-react';
import { useState } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { useAuthStore } from '@/stores/auth-store';
import type { User } from '@/types/auth';
type Role = User['role'];

const PRIMARY_NAV: { title: string; url: string; icon: React.ElementType; roles: Role[] }[] = [
  { title: 'Home', url: '/dashboard', icon: LayoutDashboard, roles: ['owner', 'receptionist'] },
  { title: 'POS', url: '/dashboard/pos', icon: CreditCard, roles: ['owner', 'receptionist', 'staff'] },
  { title: 'Bills', url: '/dashboard/bills', icon: Receipt, roles: ['owner', 'receptionist'] },
];

const MORE_NAV = [
  { title: 'Customers', url: '/dashboard/customers' },
  { title: 'Inventory', url: '/dashboard/inventory' },
  { title: 'Purchases', url: '/dashboard/purchases/invoices' },
  { title: 'Expenses', url: '/dashboard/expenses' },
  { title: 'Reports', url: '/dashboard/reports' },
  { title: 'Settings', url: '/dashboard/settings' },
];

export function NavBottom() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuthStore();
  const [moreOpen, setMoreOpen] = useState(false);

  if (!user) return null;
  const visibleNav = PRIMARY_NAV.filter(item => item.roles.includes(user.role));

  const isActive = (url: string) =>
    pathname === url || (url !== '/dashboard' && pathname.startsWith(url + '/'));

  const isMoreActive = MORE_NAV.some(item => isActive(item.url));

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden border-t border-border-subtle bg-surface-sidebar">
        {visibleNav.map((item) => (
          <button
            key={item.url}
            onClick={() => router.push(item.url)}
            className={`relative flex flex-col items-center justify-center flex-1 py-2 gap-1 text-[10px] transition-colors ${
              isActive(item.url)
                ? 'text-accent'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {isActive(item.url) && (
              <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-accent rounded-full" />
            )}
            <item.icon className="h-5 w-5" />
            <span>{item.title}</span>
          </button>
        ))}
        <button
          onClick={() => setMoreOpen(true)}
          className={`relative flex flex-col items-center justify-center flex-1 py-2 gap-1 text-[10px] transition-colors ${
            isMoreActive ? 'text-accent' : 'text-text-muted hover:text-text-secondary'
          }`}
        >
          {isMoreActive && (
            <span className="absolute top-0 left-1/2 -translate-x-1/2 w-8 h-0.5 bg-accent rounded-full" />
          )}
          <MoreHorizontal className="h-5 w-5" />
          <span>More</span>
        </button>
      </nav>

      <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
        <SheetContent side="bottom" className="bg-surface-card border-border-subtle rounded-t-xl">
          <SheetHeader className="mb-4">
            <SheetTitle className="text-text-primary">More</SheetTitle>
          </SheetHeader>
          <div className="grid grid-cols-3 gap-3 pb-6">
            {MORE_NAV.map((item) => (
              <button
                key={item.url}
                onClick={() => { router.push(item.url); setMoreOpen(false); }}
                className="flex items-center justify-center py-3 px-2 rounded-lg bg-surface-row text-text-secondary hover:bg-surface-hover hover:text-text-primary text-sm transition-colors"
              >
                {item.title}
              </button>
            ))}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
