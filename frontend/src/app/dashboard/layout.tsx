import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { ProtectedRoute } from "@/components/protected-route"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ProtectedRoute>
      <SidebarProvider>
        <AppSidebar />
        <main className="w-full h-screen overflow-hidden flex flex-col bg-slate-50">
          <header className="h-14 border-b bg-white px-4 flex items-center justify-between shrink-0 z-10 sticky top-0">
            <div className="flex items-center gap-2">
              <SidebarTrigger />
              <div className="h-4 w-px bg-slate-200 mx-2" />
              <h1 className="text-sm font-medium text-slate-600">Dashboard</h1>
            </div>
            <div className="flex items-center gap-4">
              {/* Add header actions here later (Notifications, Search) */}
            </div>
          </header>
          <div className="flex-1 overflow-auto p-6 relative">
             {children}
          </div>
        </main>
      </SidebarProvider>
    </ProtectedRoute>
  )
}
