import { useEffect, useMemo, useRef, useState } from "react";
import * as maplibre from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { type TelegramUser } from "./auth/AuthProvider";
import { MAP_CENTER, PERSONAL_ROLES, ROLE_LABELS, STYLE_URL } from "./map/constants";
import {
  createClusterMarker,
  createPointMarker,
  removePointMarker,
} from "./map/pointMarkers";
import {
  fetchPointsViewport,
  requestPointsViewport,
  usePointsSocket,
  type SocketStatus,
} from "./map/usePointsSocket";
import type { Point } from "./map/types";

export default function GeoMapWidget({ user }: { user: TelegramUser }) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibre.Map | null>(null);
  const markersRef = useRef(
    new Map<string, { marker: maplibre.Marker; signature: string }>(),
  );
  const clusterMarkersRef = useRef(new Map<string, maplibre.Marker>());

  const [points, setPoints] = useState<Point[]>([]);
  const [personalPoints, setPersonalPoints] = useState<Point[]>([]);
  const [showPersonal, setShowPersonal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(false);
  const [pointsError, setPointsError] = useState<string | null>(null);
  const [socketStatus, setSocketStatus] = useState<SocketStatus>("connecting");
  const [viewportRevision, setViewportRevision] = useState(0);
  const httpRequestRef = useRef<AbortController | null>(null);

  const canViewPersonal = PERSONAL_ROLES.includes(
    user.role as typeof PERSONAL_ROLES[number],
  );
  const socketRef = usePointsSocket({
    onAllPoints: setPoints,
    onPersonalPoints: setPersonalPoints,
    onStatus: setSocketStatus,
  });

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
    map.on("error", () => setMapError(true));
    map.once("load", () => setMapReady(true));
    mapRef.current = map;
    const clusterMarkers = clusterMarkersRef.current;

    return () => {
      markersRef.current.forEach(({ marker }) => removePointMarker(marker));
      markersRef.current.clear();
      clusterMarkers.forEach((marker) => marker.remove());
      clusterMarkers.clear();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!mapReady || !map) return;

    const syncViewport = () => {
      const bounds = map.getBounds();
      const viewport = {
        west: bounds.getWest(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        north: bounds.getNorth(),
      };
      const scope = showPersonal && canViewPersonal ? "personal" : "all";
      requestPointsViewport(socketRef.current, viewport, scope);
      setViewportRevision((revision) => revision + 1);

      if (socketStatus !== "connected") {
        httpRequestRef.current?.abort();
        const controller = new AbortController();
        httpRequestRef.current = controller;
        void fetchPointsViewport(viewport, scope).then((loadedPoints) => {
          if (controller.signal.aborted) return;
          setPointsError(null);
          if (scope === "personal") setPersonalPoints(loadedPoints);
          else setPoints(loadedPoints);
        }).catch((error: unknown) => {
          if (controller.signal.aborted) return;
          setPointsError(error instanceof Error ? error.message : "Не удалось загрузить точки.");
        });
      }
    };

    syncViewport();
    map.on("moveend", syncViewport);
    return () => {
      map.off("moveend", syncViewport);
    };
  }, [canViewPersonal, mapReady, showPersonal, socketRef, socketStatus]);

  const visiblePoints = useMemo(
    () => showPersonal && canViewPersonal ? personalPoints : points,
    [canViewPersonal, personalPoints, points, showPersonal],
  );

  const filteredPoints = useMemo(() => {
    const query = searchQuery.trim().toLocaleLowerCase();
    if (!query) return visiblePoints;
    return visiblePoints.filter((point) => [
      point.title,
      point.description ?? "",
      point.point_type,
    ].some((value) => value.toLocaleLowerCase().includes(query)));
  }, [searchQuery, visiblePoints]);

  useEffect(() => {
    if (!mapReady || !mapRef.current) return;

    const clusterGroups = new Map<string, Point[]>();
    filteredPoints.forEach((point) => {
      const projected = mapRef.current!.project([point.lng, point.lat]);
      const key = `${Math.floor(projected.x / 54)}:${Math.floor(projected.y / 54)}`;
      const group = clusterGroups.get(key) ?? [];
      group.push(point);
      clusterGroups.set(key, group);
    });
    const visibleClusters = Array.from(clusterGroups.values()).filter((group) => group.length > 1);
    const clusteredIds = new Set(visibleClusters.flatMap((group) => group.map((point) => point.id)));

    const nextMarkers = new Map<
      string,
      { marker: maplibre.Marker; signature: string }
    >();
    const visibleIds = new Set(filteredPoints.map((point) => point.id));

    markersRef.current.forEach(({ marker }, pointId) => {
      if (!visibleIds.has(pointId) || clusteredIds.has(pointId)) {
        removePointMarker(marker);
      }
    });
    clusterMarkersRef.current.forEach((marker) => marker.remove());
    clusterMarkersRef.current.clear();

    filteredPoints.forEach((point) => {
      if (clusteredIds.has(point.id)) return;
      const signature = JSON.stringify([
        point.lat,
        point.lng,
        point.title,
        point.description,
        point.point_type,
        point.point_type_icon,
        point.photo_url,
        point.likes,
        point.dislikes,
        showPersonal && canViewPersonal,
      ]);
      const existing = markersRef.current.get(point.id);

      if (existing?.signature === signature) {
        nextMarkers.set(point.id, existing);
        return;
      }

      if (existing) {
        removePointMarker(existing.marker);
      }
      nextMarkers.set(point.id, {
        marker: createPointMarker(mapRef.current!, point, {
          canDeactivate: showPersonal && canViewPersonal,
        }),
        signature,
      });
    });

    visibleClusters.forEach((group) => {
      const center = group.reduce(
        (result, point) => ({ lng: result.lng + point.lng, lat: result.lat + point.lat }),
        { lng: 0, lat: 0 },
      );
      const key = group.map((point) => point.id).sort().join(",");
      clusterMarkersRef.current.set(
        key,
        createClusterMarker(
          mapRef.current!,
          group.length,
          center.lng / group.length,
          center.lat / group.length,
        ),
      );
    });

    markersRef.current = nextMarkers;
  }, [canViewPersonal, filteredPoints, mapReady, showPersonal, viewportRevision]);

  const moveToUserLocation = () => {
    if (!navigator.geolocation || !mapRef.current) {
      setPointsError("Геолокация недоступна в этом браузере.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setPointsError(null);
        mapRef.current?.easeTo({
          center: [coords.longitude, coords.latitude],
          zoom: Math.max(mapRef.current.getZoom(), 14),
        });
      },
      () => setPointsError("Не удалось определить ваше местоположение."),
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 60_000 },
    );
  };

  return (
    <div className="map-shell">
      <div className="map-toolbar">
        <span>{user.first_name || user.username || "Пользователь"}</span>
        <span className="role-badge">{ROLE_LABELS[user.role]}</span>
        <label className="map-search">
          <span className="sr-only">Поиск точек</span>
          <input
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Поиск"
            aria-label="Поиск точек на текущей карте"
          />
        </label>
        <button type="button" className="location-button" onClick={moveToUserLocation}>
          Моё местоположение
        </button>
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
        <span className="point-count" aria-live="polite">Точек: {filteredPoints.length}</span>
      </div>
      {!mapReady && !mapError && <div className="map-status">Загружаем карту…</div>}
      {(mapError || pointsError) && (
        <div className="map-status map-status-error" role="alert">
          {mapError
            ? "Не удалось загрузить карту. Проверьте соединение и попробуйте открыть приложение ещё раз."
            : pointsError}
        </div>
      )}
      {!mapError && !pointsError && (
        <div className={`connection-status connection-status-${socketStatus}`} role="status">
          {socketStatus === "connected" ? "Синхронизировано" : "Подключение к карте…"}
        </div>
      )}
      <div ref={mapContainerRef} className="map-container" />
    </div>
  );
}
