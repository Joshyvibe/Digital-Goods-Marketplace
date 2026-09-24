"use client";

import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { clearSessionHint, setSessionHint } from "@/lib/sessionHint";
import * as authApi from "../api";
import type { LoginPayload, RegisterPayload, User } from "../types";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  logout: () => Promise<void>;
  deleteAccount: () => Promise<"deleted" | "deactivated">;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const hasRestoredSession = useRef(false);

  useEffect(() => {
    // React Strict Mode double-invokes effects in dev, which would otherwise fire this
    // twice on every full page load. With ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION
    // on the backend, the second call reuses a refresh token the first call just rotated
    // out and blacklisted, so it 401s — and since both calls independently call setUser(),
    // whichever one resolves last wins, sometimes wiping out the session that the first
    // call just successfully restored. This guard makes the restore genuinely run once.
    if (hasRestoredSession.current) return;
    hasRestoredSession.current = true;

    authApi
      .tryRestoreSession()
      .then((restoredUser) => {
        setUser(restoredUser);
        if (restoredUser) setSessionHint();
        else clearSessionHint();
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (payload: LoginPayload) => {
    const data = await authApi.login(payload);
    setUser(data.user);
    setSessionHint();
  };

  const register = async (payload: RegisterPayload) => {
    const data = await authApi.register(payload);
    setUser(data.user);
    setSessionHint();
  };

  const loginWithGoogle = async (idToken: string) => {
    const data = await authApi.loginWithGoogle(idToken);
    setUser(data.user);
    setSessionHint();
  };

  const logout = async () => {
    await authApi.logout();
    setUser(null);
    clearSessionHint();
  };

  const deleteAccount = async () => {
    const { outcome } = await authApi.deleteAccount();
    setUser(null);
    clearSessionHint();
    return outcome;
  };

  return (
    <AuthContext.Provider
      value={{ user, isLoading, login, register, loginWithGoogle, logout, deleteAccount }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
