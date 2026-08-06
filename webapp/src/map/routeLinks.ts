export function openRoute(button: Element, lat: number, lng: number) {
  if (!isAppleDevice()) {
    window.location.href = "geo:" + lat + "," + lng + "?q=" + lat + "," + lng;
    return;
  }

  const chooser = document.createElement("div");
  chooser.style.cssText = "display:flex;gap:6px;flex-wrap:wrap;margin-top:8px";

  getMapAppLinks(lat, lng).forEach(([label, appUrl, webUrl]) => {
    const link = document.createElement("a");
    link.textContent = label;
    link.href = appUrl;
    link.target = "_blank";
    link.rel = "noopener";
    link.style.cssText = "border:0;border-radius:7px;padding:6px 8px;background:#2563eb;color:white;text-decoration:none;font-size:12px";
    link.addEventListener("click", () => {
      window.setTimeout(() => {
        if (document.visibilityState === "visible") window.location.href = webUrl;
      }, 700);
    });
    chooser.appendChild(link);
  });

  button.replaceWith(chooser);
}

function isAppleDevice() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent);
}

function getMapAppLinks(lat: number, lng: number): [string, string, string][] {
  return [
    ["Apple Maps", "maps://?daddr=" + lat + "," + lng, "https://maps.apple.com/?daddr=" + lat + "," + lng],
    ["Google Maps", "comgooglemaps://?daddr=" + lat + "," + lng, "https://www.google.com/maps/dir/?api=1&destination=" + lat + "," + lng],
    ["Yandex Maps", "yandexmaps://maps.yandex.ru/?rtext=~" + lat + "," + lng + "&rtt=auto", "https://yandex.ru/maps/?rtext=~" + lat + "," + lng + "&rtt=auto"],
    ["2ГИС", "dgis://2gis.ru/routeSearch/rsType/car/to/" + lng + "," + lat, "https://2gis.ru/routeSearch/rsType/car/to/" + lng + "," + lat],
  ];
}
