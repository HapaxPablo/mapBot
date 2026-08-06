import { useEffect, useRef } from "react";
import { API_URL, SOCKET_PATH, TOKEN_KEY } from "./constants";
import type { Point, PointsMessage } from "./types";

interface UsePointsSocketOptions {
  onAllPoints: (points: Point[]) => void;
  onPersonalPoints: (points: Point[]) => void;
}

export function usePointsSocket({
  onAllPoints,
  onPersonalPoints,
}: UsePointsSocketOptions) {
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const socket = new WebSocket(createSocketUrl());
    socketRef.current = socket;

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data) as PointsMessage;
      if (message.type !== "points") return;

      if (message.scope === "personal") {
        onPersonalPoints(message.points ?? []);
      } else {
        onAllPoints(message.points ?? []);
      }
    };

    socket.onerror = (event) => console.error("Points WebSocket error:", event);
    socket.onclose = () => {
      if (socketRef.current === socket) socketRef.current = null;
    };

    return () => {
      socket.close();
      if (socketRef.current === socket) socketRef.current = null;
    };
  }, [onAllPoints, onPersonalPoints]);

  return socketRef;
}

export function requestPersonalPoints(socket: WebSocket | null) {
  if (socket?.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ scope: "personal", point_type: null }));
}

function createSocketUrl() {
  const url = new URL((API_URL || window.location.origin) + SOCKET_PATH);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";

  const token = localStorage.getItem(TOKEN_KEY);
  if (token) url.searchParams.set("token", token);

  return url;
}
