// webapp/src/App.tsx
import { lazy, Suspense } from "react";
import { useAuth } from "./auth/AuthProvider";

const GeoMapWidget = lazy(() => import("./GeoMapWidget"));

export default function App() {
  const { loading, error, user } = useAuth();

  if (loading) return <div className="auth-state">Выполняется вход через Telegram…</div>;
  if (error || !user) return <div className="auth-state auth-error">{error ?? "Пользователь не найден."}</div>;

  return (
    <Suspense fallback={<div className="auth-state">Загружается карта…</div>}>
      <GeoMapWidget user={user} />
    </Suspense>
  );
}
