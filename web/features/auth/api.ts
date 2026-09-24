import { apiFetch, refreshAccessToken, setAccessToken } from "@/lib/apiClient";
import type { AuthResponse, LoginPayload, RegisterPayload, User } from "./types";

// The refresh cookie is HttpOnly, so credentials: "include" (default in apiFetch) is what
// actually authenticates these calls — the browser attaches it, JS never touches it.

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>("/api/auth/register/", { body: payload, skipAuth: true });
  setAccessToken(data.access);
  return data;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>("/api/auth/token/", { body: payload, skipAuth: true });
  setAccessToken(data.access);
  return data;
}

export async function loginWithGoogle(idToken: string): Promise<AuthResponse> {
  const data = await apiFetch<AuthResponse>("/api/auth/google/", {
    body: { id_token: idToken },
    skipAuth: true,
  });
  setAccessToken(data.access);
  return data;
}

export async function logout(): Promise<void> {
  await apiFetch("/api/auth/logout/", { method: "POST" }).finally(() => setAccessToken(null));
}

export async function deleteAccount(): Promise<{ outcome: "deleted" | "deactivated" }> {
  return apiFetch<{ outcome: "deleted" | "deactivated" }>("/api/auth/me/", {
    method: "DELETE",
  }).finally(() => setAccessToken(null));
}

export async function fetchCurrentUser(): Promise<User> {
  return apiFetch<User>("/api/auth/me/");
}

/** Called once on app load to silently exchange the refresh cookie for an access token.
 * Routed through the shared refreshAccessToken() (not a direct apiFetch call) so this
 * shares its in-flight-request guard with apiFetch's own automatic 401-retry-refresh —
 * whichever one fires first, the other reuses its result instead of racing it. */
export async function tryRestoreSession(): Promise<User | null> {
  const refreshed = await refreshAccessToken();
  if (!refreshed) return null;

  try {
    return await fetchCurrentUser();
  } catch {
    return null;
  }
}
