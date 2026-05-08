"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logoutUser } from "@/lib/api-client";
import { Camera, Dog, FileText, Home, Layers, LogOut } from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/pets", label: "Pets", icon: Dog },
  { href: "/analyze", label: "Analyze", icon: Camera },
  { href: "/diet-plans", label: "Diet", icon: Layers },
  { href: "/reports", label: "Reports", icon: FileText },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile top bar */}
      <div className="flex h-14 items-center justify-between border-b border-border bg-card px-4 lg:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
            <Dog className="h-3.5 w-3.5 text-primary-foreground" />
          </div>
          <span className="font-semibold text-foreground">DietPaw</span>
        </div>
        <button
          onClick={() => logoutUser()}
          title="Sign out"
          className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>

      {/* Mobile bottom nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80 lg:hidden">
        <div className="flex">
          {navItems.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-1 flex-col items-center justify-center gap-1 py-2.5 text-xs font-medium transition-colors ${
                  active ? "text-primary" : "text-muted-foreground"
                }`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
