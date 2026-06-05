"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/providers/auth-provider";

function isSafeRelativePath(input: string | null): input is string {
  return !!input && input.startsWith("/") && !input.startsWith("//");
}

export default function SignInPage() {
  const router = useRouter();
  const { status, error, signIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [nextPath, setNextPath] = useState("/dashboard");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const next = params.get("next");
    setNextPath(isSafeRelativePath(next) ? next : "/dashboard");
  }, []);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(nextPath);
    }
  }, [status, nextPath, router]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError(null);

    if (!email.trim() || !password.trim()) {
      setFormError("Email and password are required.");
      return;
    }

    try {
      await signIn(email.trim(), password);
      router.replace(nextPath);
    } catch (submitError) {
      setFormError(submitError instanceof Error ? submitError.message : "Login failed.");
    }
  };

  const isLoading = status === "loading";

  return (
    <div className="mx-auto flex min-h-[calc(100vh-2rem)] w-full max-w-md items-center px-4 py-10">
      <div className="w-full rounded-2xl border border-border bg-card p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-foreground">Sign in</h1>
        <p className="mt-1 text-sm text-muted-foreground">Access your dashboard and protected routes.</p>

        <form onSubmit={onSubmit} className="mt-5 space-y-3">
          <label className="block text-sm text-foreground">
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              required
            />
          </label>

          <label className="block text-sm text-foreground">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              required
            />
          </label>

          {(formError || error) ? (
            <p className="text-sm text-rose-600">{formError || error}</p>
          ) : null}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-60"
          >
            {isLoading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-sm text-muted-foreground">
          New here? <Link href="/signup" className="text-primary underline">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
