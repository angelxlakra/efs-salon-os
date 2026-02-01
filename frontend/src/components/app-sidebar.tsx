'use client';

import * as React from 'react';
import {
  Calendar,
  LayoutDashboard,
  Settings,
  Scissors,
  ShoppingBag,
  FileText,
  LogOut,
  User,
  Users,
  CreditCard,
  Briefcase,
  Receipt,
  Calculator,
  DollarSign,
  Package,
  ShoppingCart,
  TrendingUp,
  CalendarCheck,
} from 'lucide-react';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';
import { useAuthStore } from '@/stores/auth-store';
import { useSettingsStore } from '@/stores/settings-store';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from '@/components/ui/sidebar';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const { settings, fetchSettings } = useSettingsStore();

  React.useEffect(() => {
    if (!settings) {
      fetchSettings();
    }
  }, [settings, fetchSettings]);

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  const allNavItems = [
    {
      title: 'Dashboard',
      url: '/dashboard',
      icon: LayoutDashboard,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'My Services',
      url: '/dashboard/staff',
      icon: Briefcase,
      roles: ['staff'],
    },
    {
      title: 'Point of Sale',
      url: '/dashboard/pos',
      icon: CreditCard,
      roles: ['owner', 'receptionist', 'staff'],
    },
    {
      title: 'Bills',
      url: '/dashboard/bills',
      icon: Receipt,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'EOD Reconciliation',
      url: '/dashboard/reconciliation',
      icon: Calculator,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Inventory',
      url: '/dashboard/inventory',
      icon: Package,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Purchases',
      url: '/dashboard/purchases/invoices',
      icon: ShoppingCart,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Services',
      url: '/dashboard/services',
      icon: ShoppingBag,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Customers',
      url: '/dashboard/customers',
      icon: User,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Attendance',
      url: '/dashboard/attendance',
      icon: CalendarCheck,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Expenses',
      url: '/dashboard/expenses',
      icon: DollarSign,
      roles: ['owner'],
    },
    {
      title: 'Reports',
      url: '/dashboard/reports',
      icon: FileText,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Profit & Loss',
      url: '/dashboard/reports/profit-loss',
      icon: TrendingUp,
      roles: ['owner', 'receptionist'],
    },
    {
      title: 'Users & Staff',
      url: '/dashboard/users',
      icon: Users,
      roles: ['owner'],
    },
    {
      title: 'Settings',
      url: '/dashboard/settings',
      icon: Settings,
      roles: ['owner'],
    },
  ];

  // Filter nav items based on user role
  const navItems = allNavItems.filter((item) =>
    item.roles.includes(user?.role || '')
  );

  return (
    <Sidebar collapsible="icon" {...props} className="border-r border-sidebar-border bg-sidebar">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <div className="flex items-center gap-2 cursor-pointer">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg overflow-hidden">
                  <Image
                    src="/logo-black.svg"
                    alt="Logo"
                    width={32}
                    height={32}
                    className="object-contain"
                  />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">
                    {settings?.salon_name || 'Salon'}
                  </span>
                  <span className="truncate text-xs">
                    {settings?.salon_tagline || 'Management'}
                  </span>
                </div>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarMenu className="gap-2 p-2">
          {navItems.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton 
                asChild 
                isActive={pathname === item.url}
                tooltip={item.title}
                className="hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors"
                size="default"
              >
                <a href={item.url}>
                  <item.icon className="size-4" />
                  <span>{item.title}</span>
                </a>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <Avatar className="h-8 w-8 rounded-lg">
                    <AvatarImage src={user?.avatar_url} alt={user?.fullName || 'User'} />
                    <AvatarFallback className="rounded-lg">
                      {user?.fullName?.charAt(0) || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{user?.fullName || 'User'}</span>
                    <span className="truncate text-xs">{user?.role || 'Staff'}</span>
                  </div>
                  <User className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="bottom"
                align="end"
                sideOffset={4}
              >
                <DropdownMenuLabel className="p-0 font-normal">
                  <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                    <Avatar className="h-8 w-8 rounded-lg">
                      <AvatarImage src={user?.avatar_url} alt={user?.fullName} />
                      <AvatarFallback className="rounded-lg">
                        {user?.fullName?.charAt(0) || 'U'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="grid flex-1 text-left text-sm leading-tight">
                      <span className="truncate font-semibold">{user?.fullName}</span>
                      <span className="truncate text-xs">{user?.email}</span>
                    </div>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem onClick={() => router.push('/dashboard/settings')}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-red-500 focus:text-red-500 focus:bg-red-50">
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
