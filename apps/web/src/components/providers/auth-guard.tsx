"use client";

/**
 * Auth temporarily disabled for product testing.
 * Just renders children directly without any token check.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
