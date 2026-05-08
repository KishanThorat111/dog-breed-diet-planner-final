"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { tokenStorage } from "@/lib/api-client";

/**
 * Wraps protected routes. Redirects to /sign-in if no JWT token found.
 * Renders a blank loading state during the check to avoid flash of content.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token = tokenStorage.getToken();
    if (!token) {
      router.replace("/sign-in");
    } else {
      setChecked(true);
    }
  }, [router]);

  if (!checked) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}
