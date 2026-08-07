import { useEffect, useRef } from "react";
import { API_URL, SOCKET_PATH, TOKEN_KEY } from "./constants";
import type { Point, PointBounds, PointsMessage } from "./types";

interface UsePointsSocketOptions {
  onAllPoints: (points: Point[]) => void;
  onPersonalPoints: (points: Point[]) => void;
  onStatus?: (status: SocketStatus) => void;
}

export type SocketStatus = "connecting" | "connected" | "reconnecting";

export function usePointsSocket({
  onAllPoints,
  onPersonalPoints,
  onStatus,
}: UsePointsSocketOptions) {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    let reconnectTimer: number | undefined;
    let heartbeatTimer: number | undefined;
    let stableConnectionTimer: number | undefined;
    let reconnectAttempt = 0;

    const connect = () => {
      if (disposed) return;
      onStatus?.(reconnectAttempt > 0 ? "reconnecting" : "connecting");

      const socket = new WebSocket(createSocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        onStatus?.("connected");
        const token = sessionStorage.getItem(TOKEN_KEY);
        if (token) {
          socket.send(JSON.stringify({ type: "auth", token }));
        }
        stableConnectionTimer = window.setTimeout(() => {
          reconnectAttempt = 0;
        }, 5_000);
        heartbeatTimer = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "ping" }));
          }
        }, 25_000);
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as PointsMessage;
          if (message.type !== "points") return;

          if (message.scope === "personal") {
            onPersonalPoints(message.points ?? []);
          } else {
            onAllPoints(message.points ?? []);
          }
        } catch (error) {
          console.error("Invalid points WebSocket message:", error);
        }
      };

      socket.onerror = (event) => console.error("Points WebSocket error:", event);
      socket.onclose = () => {
        if (heartbeatTimer !== undefined) window.clearInterval(heartbeatTimer);
        if (stableConnectionTimer !== undefined) window.clearTimeout(stableConnectionTimer);
        if (socketRef.current === socket) socketRef.current = null;
        if (disposed) return;
        onStatus?.("reconnecting");

        const delay = Math.min(30_000, 1_000 * 2 ** reconnectAttempt);
        reconnectAttempt += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      if (heartbeatTimer !== undefined) window.clearInterval(heartbeatTimer);
      if (stableConnectionTimer !== undefined) window.clearTimeout(stableConnectionTimer);
      socketRef.current?.close();
      socketRef.current = null;
    };
  }, [onAllPoints, onPersonalPoints, onStatus]);

  return socketRef;
}

export function requestPointsViewport(
  socket: WebSocket | null,
  bounds: PointBounds,
  scope: "all" | "personal" = "all",
) {
  if (socket?.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({
    type: "viewport",
    scope,
    point_type: null,
    bounds,
  }));
}

export async function fetchPointsViewport(
  bounds: PointBounds,
  scope: "all" | "personal" = "all",
  token: string | null = sessionStorage.getItem(TOKEN_KEY),
): Promise<Point[]> {
  const url = new URL(`${API_URL || window.location.origin}/api/points/`);
  url.searchParams.set("bbox", [bounds.west, bounds.south, bounds.east, bounds.north].join(","));
  if (scope === "personal") url.searchParams.set("scope", "personal");

  const response = await fetch(url, {
    headers: token ? { Authorization: `Token ${token}` } : {},
  });
  const payload = await response.json().catch(() => ({})) as Point[] | { results?: Point[]; detail?: string };
  if (!response.ok) {
    throw new Error("detail" in payload && payload.detail ? payload.detail : "Не удалось загрузить точки.");
  }
  return Array.isArray(payload) ? payload : payload.results ?? [];
}

function createSocketUrl() {
  const url = new URL((API_URL || window.location.origin) + SOCKET_PATH);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  return url;
}
