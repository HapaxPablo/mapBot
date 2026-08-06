import * as maplibre from "maplibre-gl";
import { createElement } from "react";
import { createRoot } from "react-dom/client";
import { MapPin } from "lucide-react";
import dynamicIconImports from "lucide-react/dynamicIconImports";
import { authHeaders } from "../auth/AuthProvider";
import { API_URL, TOKEN_KEY } from "./constants";
import type { Point } from "./types";
import { openRoute } from "./routeLinks";

export function createPointMarker(
  map: maplibre.Map,
  point: Point,
  options: { canDeactivate: boolean },
) {
  const element = document.createElement("div");
  element.className = "point-marker";
  element.appendChild(createLucideIcon(point.point_type_icon));

  const popup = new maplibre.Popup({ offset: 20 }).setHTML(
    buildPopupHtml(point, options.canDeactivate),
  );
  popup.on("open", () => {
    const button = popup.getElement()?.querySelector("[data-route-button]");
    button?.addEventListener("click", () => openRoute(button, point.lat, point.lng));

    const deactivateButton = popup.getElement()?.querySelector("[data-deactivate-button]");
    deactivateButton?.addEventListener("click", () => deactivatePoint(point.id, deactivateButton));
  });

  return new maplibre.Marker({ element })
    .setLngLat([point.lng, point.lat])
    .setPopup(popup)
    .addTo(map);
}

function createLucideIcon(iconName: string) {
  const element = document.createElement("span");
  element.className = "point-marker-icon";
  const root = createRoot(element);
  const iconKey = toLucideIconKey(iconName);
  const loadIcon = dynamicIconImports[iconKey as keyof typeof dynamicIconImports]
    ?? dynamicIconImports["map-pin"];

  root.render(createIcon(MapPin));
  void loadIcon().then(({ default: Icon }) => {
    root.render(createIcon(Icon));
  });

  return element;
}

function createIcon(Icon: typeof MapPin) {
  return createElement(Icon, {
    size: 38,
    strokeWidth: 1.8,
    color: "#2563eb",
    fill: "white",
    "aria-hidden": true,
  });
}

function toLucideIconKey(iconName: string) {
  return iconName
    .replace(/([a-z0-9])([A-Z])/g, "$1-$2")
    .toLowerCase();
}

function buildPopupHtml(point: Point, canDeactivate: boolean) {
  const photo = point.photo_url
    ? "<img src=\"" + point.photo_url + "\" style=\"width:220px;height:120px;object-fit:cover;border-radius:8px\">"
    : "";

  return [
    "<div style=\"max-width:240px\">",
    photo,
    "<h3 style=\"margin:8px 0;font-size:16px\">" + escapeHtml(point.title) + "</h3>",
    "<p style=\"margin:0;font-size:14px\">" + escapeHtml(point.description || "") + "</p>",
    "<p style=\"margin:4px 0 8px;font-size:12px;color:#666\">❤️ ",
    String(point.likes),
    " · 👎 ",
    String(point.dislikes),
    "</p>",
    "<div style=\"display:flex;gap:6px;flex-wrap:wrap\">",
    "<button type=\"button\" data-route-button style=\"border:0;border-radius:7px;padding:7px 10px;background:#2563eb;color:white;cursor:pointer\">Построить маршрут</button>",
    canDeactivate
      ? "<button type=\"button\" data-deactivate-button style=\"border:0;border-radius:7px;padding:7px 10px;background:#dc2626;color:white;cursor:pointer\">Скрыть точку</button>"
      : "",
    "</div>",
    "</div>",
  ].join("");
}

async function deactivatePoint(pointId: string, button: Element) {
  if (!(button instanceof HTMLButtonElement)) return;
  button.disabled = true;
  button.textContent = "Скрываем...";

  try {
    const response = await fetch(
      API_URL + "/api/points/" + pointId + "/deactivate/",
      {
        method: "POST",
        headers: authHeaders(localStorage.getItem(TOKEN_KEY)),
      },
    );
    if (!response.ok) throw new Error("Point deactivation failed: " + response.status);
  } catch (error) {
    console.error("Failed to deactivate point:", error);
    button.disabled = false;
    button.textContent = "Скрыть точку";
  }
}

function escapeHtml(value = "") {
  const element = document.createElement("div");
  element.textContent = value;
  return element.innerHTML;
}
