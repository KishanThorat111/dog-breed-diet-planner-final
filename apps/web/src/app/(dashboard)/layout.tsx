import { Sidebar } from "@/components/layout/sidebar";
import { MobileNav } from "@/components/layout/mobile-nav";
import { AuthGuard } from "@/components/providers/auth-guard";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Sidebar — desktop only */}
        <Sidebar />
        {/* Main content */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Mobile top nav */}
          <MobileNav />
          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 animate-fade-in">
            {children}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
