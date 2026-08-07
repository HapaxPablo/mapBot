import * as maplibre from "maplibre-gl";
import { createElement } from "react";
import { createRoot } from "react-dom/client";
import {
  Building2,
  Flag,
  Home,
  MapPin,
  Package,
  Warehouse,
  type LucideIcon,
} from "lucide-react";
import { authHeaders } from "../auth/AuthProvider";
import { API_URL, TOKEN_KEY } from "./constants";
import type { Point } from "./types";
import { openRoute } from "./routeLinks";

type DisposableIconElement = HTMLSpanElement & { dispose?: () => void };

const ICONS: Record<string, LucideIcon> = {
  "building-2": Building2,
  flag: Flag,
  home: Home,
  "map-pin": MapPin,
  package: Package,
  warehouse: Warehouse,
};

export function createPointMarker(
  map: maplibre.Map,
  point: Point,
  options: { canDeactivate: boolean },
) {
  const element = document.createElement("div");
  element.className = "point-marker";
  element.setAttribute("role", "button");
  element.setAttribute("tabindex", "0");
  element.setAttribute("aria-label", `Открыть точку: ${point.title}`);
  element.setAttribute("aria-haspopup", "dialog");
  element.appendChild(createLucideIcon(point.point_type_icon));

  const popup = new maplibre.Popup({ offset: 20 }).setHTML(
    buildPopupHtml(point, options.canDeactivate),
  );
  let popupInteractionsBound = false;
  popup.on("open", () => {
    if (popupInteractionsBound) return;
    popupInteractionsBound = true;

    const button = popup.getElement()?.querySelector("[data-route-button]");
    button?.addEventListener("click", () => openRoute(button, point.lat, point.lng));

    const deactivateButton = popup.getElement()?.querySelector("[data-deactivate-button]");
    deactivateButton?.addEventListener("click", () => deactivatePoint(point.id, deactivateButton));

    const photoButton = popup.getElement()?.querySelector("[data-photo-button]");
    if (photoButton && point.photo_url) {
      photoButton.addEventListener("click", () => openPhoto(point.photo_url!));
    }

    popup.getElement()?.querySelectorAll<HTMLButtonElement>("[data-vote-button]").forEach((voteButton) => {
      voteButton.addEventListener("click", () => {
        void votePoint(point.id, voteButton.dataset.vote ?? "", voteButton, popup);
      });
    });
  });

  const marker = new maplibre.Marker({ element })
    .setLngLat([point.lng, point.lat])
    .setPopup(popup)
    .addTo(map);

  element.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    marker.togglePopup();
  });

  return marker;
}

export function removePointMarker(marker: maplibre.Marker) {
  marker.getElement()
    .querySelector<DisposableIconElement>("[data-point-marker-icon]")
    ?.dispose?.();
  marker.remove();
}

export function createClusterMarker(
  map: maplibre.Map,
  count: number,
  lng: number,
  lat: number,
) {
  const element = document.createElement("button");
  element.type = "button";
  element.className = "point-cluster";
  element.textContent = String(count);
  element.setAttribute("aria-label", `Показать ${count} точки`);

  const marker = new maplibre.Marker({ element })
    .setLngLat([lng, lat])
    .addTo(map);
  const zoomIn = () => map.easeTo({ center: [lng, lat], zoom: map.getZoom() + 2 });
  element.addEventListener("click", zoomIn);
  element.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    zoomIn();
  });
  return marker;
}

function createLucideIcon(iconName: string) {
  const element = document.createElement("span") as DisposableIconElement;
  element.className = "point-marker-icon";
  element.dataset.pointMarkerIcon = "true";
  const root = createRoot(element);
  let disposed = false;
  element.dispose = () => {
    if (disposed) return;
    disposed = true;
    root.unmount();
  };
  const Icon = ICONS[toLucideIconKey(iconName)] ?? MapPin;
  root.render(createIcon(Icon));

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
    ? [
        "<div class=\"map-popup-photo-wrap\">",
        "<button type=\"button\" class=\"map-popup-photo-trigger\" data-photo-button aria-label=\"Открыть фото в полном размере\">",
        "<img class=\"map-popup-photo\" src=\"",
        escapeHtml(point.photo_url),
        "\" alt=\"Фото точки\">",
        "</button>",
        "<span class=\"map-popup-type\">",
        escapeHtml(point.point_type),
        "</span>",
        "</div>",
      ].join("")
    : [
        "<div class=\"map-popup-photo-wrap map-popup-photo-placeholder\">",
        "<span class=\"map-popup-placeholder-icon\">📍</span>",
        "<span class=\"map-popup-type\">",
        escapeHtml(point.point_type),
        "</span>",
        "</div>",
      ].join("");

  return [
    "<article class=\"map-popup-card\">",
    photo,
    "<div class=\"map-popup-body\">",
    "<h3 class=\"map-popup-title\">" + escapeHtml(point.title) + "</h3>",
    point.description
      ? "<p class=\"map-popup-description\">" + escapeHtml(point.description) + "</p>"
      : "<p class=\"map-popup-description is-muted\">Описание не добавлено</p>",
    "<div class=\"map-popup-votes\" aria-label=\"Оценить точку\">",
    "<button type=\"button\" class=\"map-popup-vote vote-like\" data-vote-button data-vote=\"like\">",
    "<span class=\"map-popup-vote-icon\">♥</span>",
    "<span data-vote-count=\"like\">",
    String(point.likes),
    "</span>",
    "<span class=\"map-popup-vote-label\">Нравится</span>",
    "</button>",
    "<button type=\"button\" class=\"map-popup-vote vote-dislike\" data-vote-button data-vote=\"dislike\">",
    "<span class=\"map-popup-vote-icon\">✕</span>",
    "<span data-vote-count=\"dislike\">",
    String(point.dislikes),
    "</span>",
    "<span class=\"map-popup-vote-label\">Не нравится</span>",
    "</button>",
    "</div>",
    "<div class=\"map-popup-status\" data-vote-status role=\"status\"></div>",
    "<div class=\"map-popup-actions\">",
    "<button type=\"button\" class=\"map-popup-route\" data-route-button>Построить маршрут</button>",
    canDeactivate
      ? "<button type=\"button\" class=\"map-popup-deactivate\" data-deactivate-button>Скрыть точку</button>"
      : "",
    "</div>",
    "</div>",
    "</article>",
  ].join("");
}

function openPhoto(photoUrl: string) {
  const photoWindow = window.open(photoUrl, "_blank", "noopener,noreferrer");
  if (photoWindow) photoWindow.opener = null;
}

async function votePoint(
  pointId: string,
  voteType: string,
  clickedButton: HTMLButtonElement,
  popup: maplibre.Popup,
) {
  if (voteType !== "like" && voteType !== "dislike") return;

  const popupElement = popup.getElement();
  if (!popupElement) return;
  const buttons = Array.from(popupElement.querySelectorAll<HTMLButtonElement>("[data-vote-button]"));
  const status = popupElement.querySelector<HTMLElement>("[data-vote-status]");
  clickedButton.disabled = true;
  buttons.forEach((button) => {
    button.classList.add("is-loading");
  });
  if (status) status.textContent = "Сохраняем оценку…";

  try {
    const response = await fetch(
      `${API_URL}/api/points/${pointId}/${voteType}/`,
      {
        method: "POST",
        headers: {
          ...authHeaders(sessionStorage.getItem(TOKEN_KEY)),
          "Content-Type": "application/json",
        },
      },
    );
    const payload = await response.json().catch(() => ({})) as {
      likes?: number;
      dislikes?: number;
      detail?: string;
    };
    if (!response.ok) {
      throw new Error(payload.detail ?? "Не удалось сохранить оценку.");
    }

    const likeCount = popupElement.querySelector<HTMLElement>("[data-vote-count=like]");
    const dislikeCount = popupElement.querySelector<HTMLElement>("[data-vote-count=dislike]");
    if (likeCount && payload.likes !== undefined) likeCount.textContent = String(payload.likes);
    if (dislikeCount && payload.dislikes !== undefined) dislikeCount.textContent = String(payload.dislikes);
    if (status) status.textContent = "Спасибо за вашу оценку";
    clickedButton.classList.add("is-selected");
  } catch (error) {
    if (status) status.textContent = error instanceof Error ? error.message : "Не удалось сохранить оценку.";
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
      button.classList.remove("is-loading");
    });
  }
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
        headers: authHeaders(sessionStorage.getItem(TOKEN_KEY)),
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
