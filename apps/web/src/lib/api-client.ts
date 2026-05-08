import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Base client — no auth, for public endpoints
export const apiClient = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

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

  client.interceptors.request.use((config) => {
    const token = tokenStorage.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // Token expired or invalid — clear and redirect to login
        tokenStorage.removeToken();
        if (typeof window !== "undefined") {
          window.location.href = "/sign-in";
        }
      }
      const message = error.response?.data?.detail || "An unexpected error occurred";
      return Promise.reject(new Error(message));
    }
  );

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
