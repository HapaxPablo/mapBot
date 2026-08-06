import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibre from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { type TelegramUser } from "./auth/AuthProvider";
import { MAP_CENTER, PERSONAL_ROLES, ROLE_LABELS, STYLE_URL } from "./map/constants";
import { createPointMarker } from "./map/pointMarkers";
import { requestPersonalPoints, usePointsSocket } from "./map/usePointsSocket";
import type { Point } from "./map/types";

export default function GeoMapWidget({ user }: { user: TelegramUser }) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibre.Map | null>(null);
  const markersRef = useRef<maplibre.Marker[]>([]);

  const [points, setPoints] = useState<Point[]>([]);
  const [personalPoints, setPersonalPoints] = useState<Point[]>([]);
  const [showPersonal, setShowPersonal] = useState(false);
  const [mapReady, setMapReady] = useState(false);

  const canViewPersonal = PERSONAL_ROLES.includes(
    user.role as typeof PERSONAL_ROLES[number],
  );
  const socketRef = usePointsSocket({
    onAllPoints: setPoints,
    onPersonalPoints: setPersonalPoints,
  });

  useEffect(() => {
    if (showPersonal && canViewPersonal) {
      requestPersonalPoints(socketRef.current);
    }
  }, [canViewPersonal, showPersonal, socketRef]);

  useEffect(() => {
    const container = mapContainerRef.current;
    if (!container || mapRef.current) return;

    const map = new maplibre.Map({
      container,
      style: STYLE_URL,
      center: MAP_CENTER,
      zoom: 12,
      attributionControl: false,
    });

    map.addControl(new maplibre.NavigationControl(), "top-right");
    map.once("load", () => setMapReady(true));
    mapRef.current = map;

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      map.remove();
      mapRef.current = null;
    };
  }, []);

  const visiblePoints = useMemo(
    () => showPersonal && canViewPersonal ? personalPoints : points,
    [canViewPersonal, personalPoints, points, showPersonal],
  );

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = visiblePoints.map((point) =>
      createPointMarker(mapRef.current!, point, {
        canDeactivate: showPersonal && canViewPersonal,
      }),
    );
  }, [canViewPersonal, mapReady, showPersonal, visiblePoints]);

  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span>{user.first_name || user.username || "Пользователь"}</span>
        <span className="role-badge">{ROLE_LABELS[user.role]}</span>
        {canViewPersonal && (
          <button
            type="button"
            className={showPersonal ? "layer-button active" : "layer-button"}
            onClick={() => setShowPersonal((visible) => !visible)}
            aria-pressed={showPersonal}
          >
            {showPersonal ? "Все точки" : "Мои точки"}
          </button>
        )}
      </div>
      <div ref={mapContainerRef} className="map-container" />
    </div>
  );
}
