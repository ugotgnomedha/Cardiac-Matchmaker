import useSWR, { useSWRConfig } from "swr";

import { apiRequest, isApiError } from "../utils/api";

export interface AuthUser {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

const CURRENT_USER_ENDPOINT = "/api/v1/auth/me";

export function useAuth() {
  const { mutate: mutateCache } = useSWRConfig();
  const { data, error, isLoading, isValidating, mutate } = useSWR<
    AuthUser | null,
    Error
  >(CURRENT_USER_ENDPOINT);

  const isUnauthorized = isApiError(error) && error.status === 401;
  const user = isUnauthorized ? null : (data ?? null);

  async function login(payload: LoginPayload) {
    await apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    await mutate();
  }

  async function logout() {
    try {
      await apiRequest("/api/v1/auth/logout", { method: "POST" });
    } finally {
      await mutateCache(CURRENT_USER_ENDPOINT, null, { revalidate: false });
    }
  }

  return {
    user,
    isAuthenticated: !!user,
    isLoading,
    isValidating,
    isUnauthorized,
    error: isUnauthorized ? null : (error ?? null),
    login,
    logout,
    refresh: mutate,
  };
}
