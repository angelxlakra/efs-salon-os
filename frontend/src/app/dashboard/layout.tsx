import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { ProtectedRoute } from "@/components/protected-route"
import { NavBottom } from "@/components/nav-bottom"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
      <SidebarProvider>
        <AppSidebar />
        <main className="w-full h-screen overflow-hidden flex flex-col bg-surface-page">
          <header className="h-14 border-b border-border-subtle bg-surface-sidebar px-4 flex items-center justify-between shrink-0 z-10 sticky top-0">
            <div className="flex items-center gap-2">
              <SidebarTrigger className="text-text-secondary hover:text-text-primary" />
              <div className="h-4 w-px bg-border-subtle mx-2" />
              <h1 className="text-sm font-medium text-text-secondary">Dashboard</h1>
            </div>
            <div className="flex items-center gap-4">
              {/* Add header actions here later (Notifications, Search) */}
            </div>
          </header>
          <div className="flex-1 overflow-auto p-3 sm:p-4 md:p-6 pb-20 md:pb-6 relative">
             {children}
          </div>
          <NavBottom />
        </main>
      </SidebarProvider>
    </ProtectedRoute>
  )
}
