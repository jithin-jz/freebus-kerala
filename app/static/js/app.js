(function () {
  const statusEl = document.getElementById("gpsStatus");
  const nearbyResults = document.getElementById("nearbyResults");

  function t(key, fallback) {
    return window.PBF_I18N && window.PBF_I18N[key] ? window.PBF_I18N[key] : fallback;
  }

  function setStatus(message) {
    if (statusEl) {
      statusEl.textContent = message;
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function toneFor(catchability) {
    if (catchability === "catchable") {
      return "border-emerald-500 bg-emerald-50 text-emerald-950";
    }
    if (catchability === "tight") {
      return "border-amber-500 bg-amber-50 text-amber-950";
    }
    return "border-slate-300 bg-slate-50 text-slate-700";
  }

  function renderNearby(results) {
    if (!nearbyResults) {
      return;
    }
    if (!results.length) {
      nearbyResults.innerHTML = `<p class="rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">${escapeHtml(
        t("results.no_buses_soon", "No nearby buses found.")
      )}</p>`;
      return;
    }
    nearbyResults.innerHTML = results
      .map(
        (bus) => `
          <article class="rounded border p-4 shadow-sm ${toneFor(bus.catchability)}">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div class="min-w-0 space-y-2">
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="text-base font-semibold tracking-normal text-slate-950">${escapeHtml(bus.stop_name)}</h3>
                  <span class="rounded bg-white/70 px-2 py-1 text-xs font-medium">${bus.distance_metres} m</span>
                  <span class="rounded bg-white/70 px-2 py-1 text-xs font-medium">${bus.walk_minutes} min walk</span>
                </div>
                <div>
                  <h3 class="truncate text-lg font-semibold tracking-normal">${escapeHtml(bus.route_name)}</h3>
                  <p class="text-sm opacity-85">${escapeHtml(bus.origin_stop)} to ${escapeHtml(bus.destination_stop)}${
                    bus.via ? ` via ${escapeHtml(bus.via)}` : ""
                  }</p>
                </div>
                <div class="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-normal">
                  <span class="rounded bg-white/70 px-2 py-1">${escapeHtml(bus.bus_type)}</span>
                  ${bus.is_priyadarshini ? '<span class="rounded bg-white/70 px-2 py-1">Priyadarshini</span>' : ""}
                </div>
              </div>
              <div class="flex shrink-0 items-center gap-2 sm:flex-col sm:items-end">
                <span class="countdown-badge inline-flex min-w-24 items-center justify-center rounded border border-current px-3 py-1 text-sm font-semibold" data-countdown-target="${escapeHtml(
                  bus.departure_iso
                )}">${bus.minutes_until} min</span>
                <span class="text-sm font-medium">${escapeHtml(bus.departure_time)}</span>
              </div>
            </div>
          </article>
        `
      )
      .join("");
    updateCountdowns();
  }

  async function loadNearby(position) {
    const params = new URLSearchParams({
      lat: String(position.coords.latitude),
      lng: String(position.coords.longitude),
    });
    const response = await fetch(`/api/v1/nearby?${params.toString()}`, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error(`Nearby request failed: ${response.status}`);
    }
    const payload = await response.json();
    renderNearby(payload.results || []);
  }

  window.initGPS = function initGPS() {
    if (!navigator.geolocation) {
      setStatus(t("errors.gps_not_supported", "GPS not supported in this browser."));
      return;
    }
    setStatus(t("home.gps_requesting", "Requesting GPS access..."));
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const accuracy = Math.round(position.coords.accuracy || 0);
        setStatus(
          accuracy > 100
            ? t("home.gps_low_accuracy", "GPS accuracy is low - results may vary.")
            : t("home.gps_found", "Location found")
        );
        try {
          await loadNearby(position);
        } catch (_error) {
          setStatus(t("errors.gps_unknown", "Could not get your location. Please try again."));
        }
      },
      () => setStatus(t("errors.gps_unknown", "Could not get your location. Please try again.")),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
    );
  };

  function updateCountdowns() {
    document.querySelectorAll("[data-countdown-target]").forEach((el) => {
      const target = Date.parse(el.getAttribute("data-countdown-target"));
      if (Number.isNaN(target)) {
        return;
      }
      const minutes = Math.max(0, Math.round((target - Date.now()) / 60000));
      el.textContent = `${minutes} min`;
    });
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/static/js/sw.js").catch(() => {});
    });
  }

  updateCountdowns();
  window.setInterval(updateCountdowns, 30000);
})();

