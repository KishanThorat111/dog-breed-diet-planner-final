"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { tokenStorage } from "@/lib/api-client";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    const user = tokenStorage.getUser();
    if (!user) {
      // not authenticated -> redirect to sign-in
      router.push("/sign-in");
      return;
    }
    // only allow users with is_admin flag for admin routes
    if ((user as any).is_admin) {
      setAllowed(true);
    } else {
      setAllowed(false);
    }
    setReady(true);
  }, [router]);

  if (!ready) return <div>Checking authentication...</div>;
  if (!allowed) return <div>Access denied: admin only.</div>;
  return <>{children}</>;
}
