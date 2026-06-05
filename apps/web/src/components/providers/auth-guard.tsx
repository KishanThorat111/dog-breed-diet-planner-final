"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { status, error, retryCurrentUser } = useAuth();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (status !== "loading") {
      setTimedOut(false);
      return;
    }
    const timer = window.setTimeout(() => setTimedOut(true), 5000);
    return () => window.clearTimeout(timer);
  }, [status]);

  useEffect(() => {
    if (status === "unauthenticated") {
      const next = pathname && pathname !== "/" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${next}`);
    }
  }, [status, pathname, router]);

  if (status === "authenticated") {
    return <>{children}</>;
  }

  if (status === "loading" && !timedOut) {
    return <div>Checking authentication...</div>;
  }

  if (status === "error" || timedOut) {
    return (
      <div className="space-y-3 rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-medium text-foreground">Authentication check failed</p>
        <p className="text-muted-foreground">
          {error || "Authentication initialization timed out. Please retry or sign in again."}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void retryCurrentUser()}
            className="rounded-lg bg-primary px-3 py-1.5 text-primary-foreground"
          >
            Retry
          </button>
          <Link className="rounded-lg border border-border px-3 py-1.5" href="/login">
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  return <div>Redirecting to login...</div>;
}

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { status, user, error, retryCurrentUser } = useAuth();
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (status !== "loading") {
      setTimedOut(false);
      return;
    }
    const timer = window.setTimeout(() => setTimedOut(true), 5000);
    return () => window.clearTimeout(timer);
  }, [status]);

  useEffect(() => {
    if (status === "unauthenticated") {
      const next = pathname && pathname !== "/" ? `?next=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${next}`);
      return;
    }

    if (status === "authenticated" && !user?.is_admin) {
      router.replace("/dashboard");
    }
  }, [status, pathname, router, user?.is_admin]);

  if (status === "authenticated" && user?.is_admin) {
    return <>{children}</>;
  }

  if (status === "loading" && !timedOut) {
    return <div>Checking authentication...</div>;
  }

  if (status === "error" || timedOut) {
    return (
      <div className="space-y-3 rounded-xl border border-border bg-card p-4 text-sm">
        <p className="font-medium text-foreground">Admin authentication failed</p>
        <p className="text-muted-foreground">
          {error || "Authentication initialization timed out. Please retry or sign in again."}
        </p>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void retryCurrentUser()}
            className="rounded-lg bg-primary px-3 py-1.5 text-primary-foreground"
          >
            Retry
          </button>
          <Link className="rounded-lg border border-border px-3 py-1.5" href="/login">
            Go to login
          </Link>
        </div>
      </div>
    );
  }

  return <div>Redirecting...</div>;
}
