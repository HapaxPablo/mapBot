/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type Role = "admin" | "superuser" | "old_member" | "new_member";

export interface TelegramUser {
  user_id: number;
  telegram_id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: Role;
}

interface AuthContextValue {
  user: TelegramUser | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  hasRole: (...roles: Role[]) => boolean;
  can: (permission: Permission) => boolean;
}

export type Permission = "view_map" | "vote" | "create_point" | "upload_photo" | "manage_users";

const API_URL = (import.meta.env.VITE_API_URL as string | undefined ?? "").replace(/\/$/, "");
const TOKEN_KEY = "geomap.auth.token";
const AuthContext = createContext<AuthContextValue | null>(null);

const permissions: Record<Permission, Role[]> = {
  view_map: ["admin", "superuser", "old_member", "new_member"],
  vote: ["admin", "superuser", "old_member", "new_member"],
  create_point: ["admin", "superuser", "old_member"],
  upload_photo: ["admin", "superuser", "old_member"],
  manage_users: ["admin", "superuser"],
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<TelegramUser | null>(null);
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    tg?.ready();
    tg?.expand();

    async function authenticate() {
      try {
        const initData = tg?.initData;
        if (!initData) throw new Error("Откройте приложение из Telegram.");

        const response = await fetch(`${API_URL}/api/auth/telegram/webapp/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ init_data: initData }),
        });
        if (!response.ok) throw new Error((await response.json()).detail ?? "Не удалось войти.");

        const data = await response.json() as { user: TelegramUser; token: string };
        sessionStorage.setItem(TOKEN_KEY, data.token);
        setToken(data.token);
        setUser(data.user);
      } catch (authError) {
        setError(authError instanceof Error ? authError.message : "Не удалось войти.");
      } finally {
        setLoading(false);
      }
    }

    void authenticate();
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    token,
    loading,
    error,
    isAuthenticated: user !== null && token !== null,
    hasRole: (...roles) => user !== null && roles.includes(user.role),
    can: (permission) => user !== null && permissions[permission].includes(user.role),
  }), [error, loading, token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Token ${token}` } : {};
}
