import axios, { AxiosError, AxiosInstance } from "axios";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000");
const API_DEBUG = process.env.NEXT_PUBLIC_API_DEBUG === "true" || process.env.NODE_ENV !== "production";

const REQUEST_TIMEOUT_MS = 10_000;
const AUTH_TIMEOUT_MS = 5_000;
export const AUTH_UNAUTHORIZED_EVENT = "dietpaw:auth-unauthorized";

function nextRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

export class ApiClientError extends Error {
  status?: number;
  code?: string;
  isTimeout: boolean;
  isNetwork: boolean;

  constructor(
    message: string,
    options?: {
      status?: number;
      code?: string;
      isTimeout?: boolean;
      isNetwork?: boolean;
    }
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = options?.status;
    this.code = options?.code;
    this.isTimeout = !!options?.isTimeout;
    this.isNetwork = !!options?.isNetwork;
  }
}

export interface SessionUser {
  user_id: string;
  email: string;
  full_name?: string | null;
  is_admin: boolean;
  subscription?: {
    plan: string;
    status: string;
    credits_remaining: number;
    trial_ends_at: string | null;
  };
}

interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  user_id: string;
  email: string;
  full_name?: string | null;
  is_admin: boolean;
  subscription?: SessionUser["subscription"];
}

function toApiClientError(error: AxiosError): ApiClientError {
  const status = error.response?.status;
  const detail = (error.response?.data as { detail?: string } | undefined)?.detail;
  const code = error.code;
  const isTimeout = code === "ECONNABORTED";
  const isNetwork = !error.response;

  let message = detail || "An unexpected error occurred";
  if (isTimeout) {
    message = "Request timed out. Please try again.";
  } else if (isNetwork) {
    message = "Unable to reach server. Check your connection and try again.";
  }

  return new ApiClientError(message, { status, code, isTimeout, isNetwork });
}

function attachApiDebugInterceptors(client: AxiosInstance, withAuth: boolean): void {
  client.interceptors.request.use((config) => {
    const requestId = nextRequestId();
    const headers = config.headers ?? {};
    (headers as Record<string, string>)["X-Request-ID"] = requestId;

    if (withAuth) {
      const token = tokenStorage.getToken();
      if (token) {
        (headers as Record<string, string>).Authorization = `Bearer ${token}`;
      }
    }

    config.headers = headers;

    if (API_DEBUG && typeof window !== "undefined") {
      const fullUrl = `${config.baseURL ?? ""}${config.url ?? ""}`;
      console.info("[api:req]", {
        requestId,
        method: config.method?.toUpperCase(),
        url: fullUrl,
        origin: window.location.origin,
      });
    }

    return config;
  });

  client.interceptors.response.use(
    (response) => {
      if (API_DEBUG && typeof window !== "undefined") {
        const fullUrl = `${response.config.baseURL ?? ""}${response.config.url ?? ""}`;
        console.info("[api:res]", {
          status: response.status,
          url: fullUrl,
          requestId: response.headers["x-request-id"] ?? "",
        });
      }
      return response;
    },
    async (error: AxiosError) => {
      if (API_DEBUG && typeof window !== "undefined") {
        const cfg = error.config;
        const fullUrl = `${cfg?.baseURL ?? ""}${cfg?.url ?? ""}`;
        console.error("[api:err]", {
          status: error.response?.status ?? null,
          url: fullUrl,
          requestId: error.response?.headers?.["x-request-id"] ?? "",
          detail: (error.response?.data as { detail?: string } | undefined)?.detail ?? "",
          message: error.message,
        });
      }

      const statusCode = error.response?.status;
      const originalRequest = (error.config || {}) as (typeof error.config & { _retry?: boolean });
      const isAuthError = statusCode === 401;

      if (withAuth && isAuthError && originalRequest && !String(originalRequest.url || "").includes("/auth/refresh")) {
        if (!originalRequest._retry) {
          originalRequest._retry = true;
          try {
            await refreshAccessToken();
            const token = tokenStorage.getToken();
            if (token) {
              const headers = originalRequest.headers ?? {};
              (headers as Record<string, string>).Authorization = `Bearer ${token}`;
              originalRequest.headers = headers;
            }
            return client(originalRequest);
          } catch {
            // Fall through to hard logout below.
          }
        }

        if (typeof window !== "undefined") {
          clearAuthSession();
          window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
        }
      }

      return Promise.reject(toApiClientError(error));
    }
  );
}

// Base clients
export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: REQUEST_TIMEOUT_MS,
});

const authedClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: REQUEST_TIMEOUT_MS,
});

attachApiDebugInterceptors(apiClient, false);
attachApiDebugInterceptors(authedClient, true);

// -- Token storage ------------------------------------------------------------
const TOKEN_KEY = "dietpaw_token";
const REFRESH_TOKEN_KEY = "dietpaw_refresh_token";
const USER_KEY = "dietpaw_user";

function authCookieFlags(): string {
  const secure = typeof window !== "undefined" && window.location.protocol === "https:";
  return `Path=/; SameSite=Lax${secure ? "; Secure" : ""}`;
}

function clearAuthCookies() {
  if (typeof window === "undefined") return;
  const flags = authCookieFlags();
  document.cookie = `dietpaw_token=; Max-Age=0; ${flags}`;
  document.cookie = `dietpaw_user=; Max-Age=0; ${flags}`;
}

function setAuthCookies(payload: AuthResponse) {
  if (typeof window === "undefined") return;
  const flags = authCookieFlags();
  const userObj: SessionUser = {
    user_id: payload.user_id,
    email: payload.email,
    full_name: payload.full_name ?? null,
    is_admin: !!payload.is_admin,
    subscription: payload.subscription,
  };
  document.cookie = `dietpaw_token=${encodeURIComponent(payload.access_token)}; ${flags}`;
  document.cookie = `dietpaw_user=${encodeURIComponent(JSON.stringify(userObj))}; ${flags}`;
}

export const tokenStorage = {
  getToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken: (token: string) => {
    if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
  },
  getRefreshToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setRefreshToken: (token: string) => {
    if (typeof window !== "undefined") localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },
  removeToken: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      clearAuthCookies();
    }
  },
  getUser: (): SessionUser | null => {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as SessionUser;
    } catch {
      return null;
    }
  },
  setUser: (user: SessionUser) => {
    if (typeof window !== "undefined") localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
};

export function setAuthSession(payload: AuthResponse): AuthResponse {
  tokenStorage.setToken(payload.access_token);
  if (payload.refresh_token) {
    tokenStorage.setRefreshToken(payload.refresh_token);
  }
  tokenStorage.setUser({
    user_id: payload.user_id,
    email: payload.email,
    full_name: payload.full_name ?? null,
    is_admin: !!payload.is_admin,
    subscription: payload.subscription,
  });
  setAuthCookies(payload);
  return payload;
}

export function clearAuthSession() {
  tokenStorage.removeToken();
}

// -- Authenticated client hook -------------------------------------------------
export function useApiClient() {
  return authedClient;
}

// -- Auth helpers --------------------------------------------------------------
export async function loginUser(email: string, password: string) {
  const res = await apiClient.post<AuthResponse>("/auth/login", { email, password }, { timeout: AUTH_TIMEOUT_MS });
  return setAuthSession(res.data);
}

export async function registerUser(email: string, password: string, full_name?: string) {
  const res = await apiClient.post<AuthResponse>(
    "/auth/register",
    { email, password, full_name },
    { timeout: AUTH_TIMEOUT_MS }
  );
  return setAuthSession(res.data);
}

export async function refreshAccessToken(refreshToken?: string) {
  const token = refreshToken || tokenStorage.getRefreshToken();
  if (!token) {
    throw new ApiClientError("Session expired. Please sign in again.", { status: 401 });
  }
  const res = await apiClient.post<AuthResponse>(
    "/auth/refresh",
    { refresh_token: token },
    { timeout: AUTH_TIMEOUT_MS }
  );
  return setAuthSession(res.data);
}

export async function getCurrentUser() {
  const res = await authedClient.get<{
    user_id: string;
    email: string;
    full_name?: string | null;
    is_admin: boolean;
    subscription?: SessionUser["subscription"];
  }>("/auth/me", { timeout: AUTH_TIMEOUT_MS });

  const current: SessionUser = {
    user_id: res.data.user_id,
    email: res.data.email,
    full_name: res.data.full_name ?? null,
    is_admin: !!res.data.is_admin,
    subscription: res.data.subscription,
  };
  tokenStorage.setUser(current);
  setAuthCookies({
    access_token: tokenStorage.getToken() || "",
    refresh_token: tokenStorage.getRefreshToken() || undefined,
    ...current,
  });
  return current;
}

export function logoutUser(redirectTo = "/login") {
  clearAuthSession();
  if (typeof window !== "undefined") {
    window.location.href = redirectTo;
  }
}
