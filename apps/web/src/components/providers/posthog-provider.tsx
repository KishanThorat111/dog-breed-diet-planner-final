// PostHog is disabled in the simplified stack.
// Re-enable by adding posthog-js to package.json and implementing this provider.
export function PHProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
