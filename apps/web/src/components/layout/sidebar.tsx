"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logoutUser, tokenStorage } from "@/lib/api-client";
import { BarChart3, Camera, Dog, FileText, Home, Layers, LogOut, User } from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/pets", label: "My Pets", icon: Dog },
  { href: "/analyze", label: "Analyze", icon: Camera },
  { href: "/diet-plans", label: "Diet Plans", icon: Layers },
  { href: "/reports", label: "Reports", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const user = tokenStorage.getUser();

  const handleLogout = () => {
    logoutUser();
    router.push("/sign-in");
  };

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-card lg:flex">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Dog className="h-4 w-4 text-primary-foreground" />
        </div>
        <span className="font-semibold text-foreground">DietPaw</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      <div className="border-t border-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
              <User className="h-4 w-4 text-muted-foreground" />
            </div>
            <span className="truncate text-sm text-muted-foreground">
              {user?.full_name || user?.email || "Account"}
            </span>
          </div>
          <button
            onClick={handleLogout}
            title="Sign out"
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}

export function AdminSidebarLink() {
  return (
    <Link
      href="/admin"
      className="flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
    >
      <BarChart3 className="h-4 w-4 shrink-0" />
      Admin
    </Link>
  );
}
