import Link from "next/link";
import { AuthGuard } from "@/components/providers/auth-guard";
import { BarChart3, Bot, Settings, Users } from "lucide-react";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden bg-background">
        {/* Admin Sidebar */}
        <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-card lg:flex">
          <div className="flex h-16 items-center gap-2 border-b border-border px-4">
            <Settings className="h-4 w-4 text-primary" />
            <span className="font-semibold text-foreground">Admin</span>
          </div>
          <nav className="flex-1 space-y-1 p-3">
            {[
              { href: "/admin", label: "Overview", icon: BarChart3 },
              { href: "/admin/users", label: "Users", icon: Users },
              { href: "/admin/ai", label: "AI Settings", icon: Bot },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </AuthGuard>
  );
}
