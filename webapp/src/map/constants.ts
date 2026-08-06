import type { TelegramUser } from "../auth/AuthProvider";

export const STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL as string;
export const API_URL = (import.meta.env.VITE_API_URL as string | undefined ?? "").replace(/\/$/, "");
export const SOCKET_PATH = "/ws/points/";
export const TOKEN_KEY = "geomap.auth.token";
export const MAP_CENTER: [number, number] = [92.8672, 56.0184];

export const PERSONAL_ROLES = ["admin", "superuser", "old_member"] as const;
export const ROLE_LABELS: Record<TelegramUser["role"], string> = {
  admin: "Администратор",
  superuser: "Суперпользователь",
  old_member: "Старый участник",
  new_member: "Новый участник",
};
