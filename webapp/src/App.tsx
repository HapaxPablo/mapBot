// webapp/src/App.tsx
import { useEffect } from "react";
import GeoMapWidget from "./GeoMapWidget";

export default function App() {
  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    tg?.ready();
    tg?.expand();
  }, []);

  return <GeoMapWidget />;
}
