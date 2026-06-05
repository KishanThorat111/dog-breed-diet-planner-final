"use client";

import {
  AUTH_UNAUTHORIZED_EVENT,
  ApiClientError,
  SessionUser,
  clearAuthSession,
  getCurrentUser,
  loginUser,
  logoutUser,
  refreshAccessToken,
  registerUser,
  tokenStorage,
} from "@/lib/api-client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface AuthContextValue {
  status: AuthStatus;
  user: SessionUser | null;
  error: string | null;
  initialized: boolean;
  initializeAuth: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, fullName?: string) => Promise<void>;
  signOut: (redirectTo?: string) => void;
  retryCurrentUser: () => Promise<void>;
}

const INIT_TIMEOUT_MS = 5_000;
const AUTH_RETRY_ATTEMPTS = 2;

const AuthContext = createContext<AuthContextValue | null>(null);

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function withAuthRetries<T>(run: () => Promise<T>, attempts = AUTH_RETRY_ATTEMPTS): Promise<T> {
  let lastError: unknown;

  for (let index = 0; index <= attempts; index += 1) {
    try {
      return await run();
    } catch (error) {
      lastError = error;
      if (error instanceof ApiClientError && (error.status === 401 || error.status === 403)) {
        throw error;
      }
      if (index >= attempts) {
        break;
      }
      await wait(250 * (index + 1));
    }
  }

  throw lastError;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<SessionUser | null>(null);
  const [error, setError] = useState<string | null>(null);
  const initializedRef = useRef(false);

  const setAuthenticated = useCallback((nextUser: SessionUser) => {
    setUser(nextUser);
    setStatus("authenticated");
    setError(null);
  }, []);

  const setUnauthenticated = useCallback((nextError: string | null = null) => {
    setUser(null);
    setStatus("unauthenticated");
    setError(nextError);
  }, []);

  const hydrateCurrentUser = useCallback(async () => {
    const refreshedUser = await withAuthRetries(() => getCurrentUser());
    setAuthenticated(refreshedUser);
  }, [setAuthenticated]);

  const tryRefreshAndHydrate = useCallback(async () => {
    await withAuthRetries(() => refreshAccessToken());
    await hydrateCurrentUser();
  }, [hydrateCurrentUser]);

  const initializeAuth = useCallback(async () => {
    setStatus("loading");
    setError(null);

    const initWork = (async () => {
      const token = tokenStorage.getToken();
      const cachedUser = tokenStorage.getUser();

      if (!token) {
        setUnauthenticated(null);
        return;
      }

      if (cachedUser) {
        // Optimistically render cached user while backend validation runs.
        setAuthenticated(cachedUser);
      }

      try {
        await hydrateCurrentUser();
      } catch (authError) {
        if (authError instanceof ApiClientError && (authError.status === 401 || authError.status === 403)) {
          try {
            await tryRefreshAndHydrate();
            return;
          } catch {
            clearAuthSession();
            setUnauthenticated("Your session expired. Please log in again.");
            return;
          }
        }

        // Network/API degradation fallback: keep cached user if available.
        if (cachedUser) {
          console.error("[auth] session restore degraded", authError);
          setAuthenticated(cachedUser);
          setError("Connection issue while validating session. Some features may be unavailable.");
          return;
        }

        throw authError;
      }
    })();

    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => {
        reject(new ApiClientError("Authentication initialization timed out.", { isTimeout: true }));
      }, INIT_TIMEOUT_MS);
    });

    try {
      await Promise.race([initWork, timeoutPromise]);
    } catch (initError) {
      console.error("[auth] initialization failed", initError);
      setStatus("error");
      setUser(null);
      setError(initError instanceof Error ? initError.message : "Failed to initialize authentication.");
    } finally {
      initializedRef.current = true;
    }
  }, [hydrateCurrentUser, setAuthenticated, setUnauthenticated, tryRefreshAndHydrate]);

  useEffect(() => {
    void initializeAuth();
  }, [initializeAuth]);

  useEffect(() => {
    const onUnauthorized = () => {
      console.warn("[auth] unauthorized event received; clearing session");
      clearAuthSession();
      setUnauthenticated("Your session is no longer valid. Please log in again.");
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, onUnauthorized as EventListener);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, onUnauthorized as EventListener);
    };
  }, [setUnauthenticated]);

  const signIn = useCallback(async (email: string, password: string) => {
    setStatus("loading");
    setError(null);
    try {
      const response = await loginUser(email, password);
      setAuthenticated({
        user_id: response.user_id,
        email: response.email,
        full_name: response.full_name ?? null,
        is_admin: !!response.is_admin,
        subscription: response.subscription,
      });
    } catch (loginError) {
      setStatus("unauthenticated");
      setError(loginError instanceof Error ? loginError.message : "Login failed.");
      throw loginError;
    }
  }, [setAuthenticated]);

  const signUp = useCallback(async (email: string, password: string, fullName?: string) => {
    setStatus("loading");
    setError(null);
    try {
      const response = await registerUser(email, password, fullName);
      setAuthenticated({
        user_id: response.user_id,
        email: response.email,
        full_name: response.full_name ?? null,
        is_admin: !!response.is_admin,
        subscription: response.subscription,
      });
    } catch (registerError) {
      setStatus("unauthenticated");
      setError(registerError instanceof Error ? registerError.message : "Sign up failed.");
      throw registerError;
    }
  }, [setAuthenticated]);

  const signOut = useCallback((redirectTo = "/login") => {
    setUnauthenticated(null);
    logoutUser(redirectTo);
  }, [setUnauthenticated]);

  const retryCurrentUser = useCallback(async () => {
    await initializeAuth();
  }, [initializeAuth]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      error,
      initialized: initializedRef.current,
      initializeAuth,
      signIn,
      signUp,
      signOut,
      retryCurrentUser,
    }),
    [status, user, error, initializeAuth, signIn, signUp, signOut, retryCurrentUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
