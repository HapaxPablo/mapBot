// webapp/src/App.tsx
import GeoMapWidget from "./GeoMapWidget";
import { useAuth } from "./auth/AuthProvider";

export default function App() {
  const { loading, error, user } = useAuth();

  if (loading) return <div className="auth-state">Выполняется вход через Telegram…</div>;
  if (error || !user) return <div className="auth-state auth-error">{error ?? "Пользователь не найден."}</div>;

  return <GeoMapWidget user={user} />;
}
