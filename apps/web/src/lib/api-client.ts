import axios, { AxiosError, AxiosInstance } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_DEBUG = process.env.NEXT_PUBLIC_API_DEBUG === "true" || process.env.NODE_ENV !== "production";

function nextRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `req_${Date.now()}_${Math.random().toString(16).slice(2)}`;
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
          acao: response.headers["access-control-allow-origin"] ?? "",
        });
      }
      return response;
    },
    (error: AxiosError) => {
      if (error.response?.status === 401) {
        tokenStorage.removeToken();
        if (typeof window !== "undefined") {
          window.location.href = "/sign-in";
        }
      }

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

      const message =
        (error.response?.data as { detail?: string } | undefined)?.detail ||
        "An unexpected error occurred";
      return Promise.reject(new Error(message));
    }
  );
}

// Base client - no auth, for public endpoints
export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

attachApiDebugInterceptors(apiClient, false);

// -- Token storage ------------------------------------------------------------
const TOKEN_KEY = "dietpaw_token";
const USER_KEY = "dietpaw_user";

export const tokenStorage = {
  getToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(TOKEN_KEY);
  },
  setToken: (token: string) => {
    if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
  },
  removeToken: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  },
  getUser: () => {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
  },
  setUser: (user: object) => {
    if (typeof window !== "undefined") localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
};

// -- Authenticated client hook -------------------------------------------------
/**
 * Returns an axios instance that automatically injects the JWT from localStorage.
 * Use this in React components.
 */
export function useApiClient() {
  const client = axios.create({
    baseURL: `${API_URL}/api/v1`,
    headers: { "Content-Type": "application/json" },
  });

  attachApiDebugInterceptors(client, true);

  return client;
}

// -- Auth helpers --------------------------------------------------------------
export async function loginUser(email: string, password: string) {
  const res = await apiClient.post("/auth/login", { email, password });
  tokenStorage.setToken(res.data.access_token);
  tokenStorage.setUser({
    user_id: res.data.user_id,
    email: res.data.email,
    full_name: res.data.full_name,
    is_admin: res.data.is_admin,
  });
  return res.data;
}

export async function registerUser(email: string, password: string, full_name?: string) {
  const res = await apiClient.post("/auth/register", { email, password, full_name });
  tokenStorage.setToken(res.data.access_token);
  tokenStorage.setUser({
    user_id: res.data.user_id,
    email: res.data.email,
    full_name: res.data.full_name,
    is_admin: res.data.is_admin,
  });
  return res.data;
}

export function logoutUser() {
  tokenStorage.removeToken();
  if (typeof window !== "undefined") {
    window.location.href = "/sign-in";
  }
}
