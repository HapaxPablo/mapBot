// webapp/src/GeoMapWidget.tsx
import { useEffect, useRef, useState } from "react";
import * as maplibre from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface Point {
  id: string;
  title: string;
  description: string | null;
  lat: number;
  lng: number;
  photo_url: string | null;
  likes: number;
  dislikes: number;
}

const STYLE_URL = import.meta.env.VITE_MAP_STYLE_URL as string;
const API_URL = import.meta.env.VITE_API_URL as string;

export default function GeoMapWidget() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibre.Map | null>(null);
  const [points, setPoints] = useState<Point[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/points/`)
      .then((r) => r.json())
      .then((data) => setPoints(data.results ?? data));
  }, []);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibre.Map({
      container: mapContainer.current,
      style: STYLE_URL,
      center: [92.8672, 56.0184],
      zoom: 12,
      attributionControl: false,
    });

    map.current.addControl(new maplibre.NavigationControl(), "top-right");
  }, []);

  useEffect(() => {
    if (!map.current || points.length === 0) return;

    points.forEach((point) => {
      const el = document.createElement("div");
      el.style.cssText =
        "width:34px;height:34px;background:#ef4444;border-radius:50%;border:3px solid white;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.3)";

      const popup = new maplibre.Popup({ offset: 20 }).setHTML(`
        <div style="max-width:240px">
          ${point.photo_url ? `<img src="${point.photo_url}" style="width:220px;height:120px;object-fit:cover;border-radius:8px">` : ""}
          <h3 style="margin:8px 0;font-size:16px">${escapeHtml(point.title)}</h3>
          <p style="margin:0;font-size:14px">${escapeHtml(point.description || "")}</p>
          <p style="margin:4px 0 0;font-size:12px;color:#666">❤️ ${point.likes} · 👎 ${point.dislikes}</p>
        </div>
      `);

      new maplibre.Marker({ element: el })
        .setLngLat([point.lng, point.lat])
        .setPopup(popup)
        .addTo(map.current!);
    });
  }, [points]);

  return <div ref={mapContainer} style={{ width: "100%", height: "100vh" }} />;
}

function escapeHtml(value = "") {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}
