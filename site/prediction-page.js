/**
 * Prediction page for static hosts: uses Flask /api/forecast when available.
 */
(function () {
  "use strict";

  let chart;
  let indiaMap;
  let mapZoom = 1;

  function mapAssetUrl() {
    return window.EVPages?.asset
      ? window.EVPages.asset("frontend/static/data/india-states.geojson")
      : "frontend/static/data/india-states.geojson";
  }

  function geometryCoordinates(geometry) {
    if (!geometry) return [];
    if (geometry.type === "Polygon") return geometry.coordinates;
    if (geometry.type === "MultiPolygon") return geometry.coordinates.flat(1);
    return [];
  }

  function projectPoint(point, bounds, width, height) {
    const pad = 8;
    const scale = Math.min(
      (width - pad * 2) / (bounds.maxX - bounds.minX || 1),
      (height - pad * 2) / (bounds.maxY - bounds.minY || 1)
    );
    const mapWidth = (bounds.maxX - bounds.minX) * scale;
    const mapHeight = (bounds.maxY - bounds.minY) * scale;
    const offsetX = (width - mapWidth) / 2;
    const offsetY = (height - mapHeight) / 2;
    return [
      offsetX + (point[0] - bounds.minX) * scale,
      height - offsetY - (point[1] - bounds.minY) * scale,
    ];
  }

  function featurePath(feature, bounds, width, height) {
    return geometryCoordinates(feature.geometry).map((ring) =>
      ring.map((point, index) => {
        const [x, y] = projectPoint(point, bounds, width, height);
        return `${index ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)}`;
      }).join(" ") + " Z"
    ).join(" ");
  }

  async function loadIndiaMap() {
    if (indiaMap) return indiaMap;
    const response = await fetch(mapAssetUrl());
    if (!response.ok) throw new Error("India map could not be loaded.");
    indiaMap = await response.json();
    return indiaMap;
  }

  async function renderForecastMap(region, target, value, period) {
    const mapEl = document.getElementById("forecastMap");
    const statusEl = document.getElementById("forecastMapStatus");
    const valueEl = document.getElementById("forecastMapValue");
    if (!mapEl) return;
    statusEl.textContent = "Loading India map…";
    try {
      const map = await loadIndiaMap();
      const features = map.features || [];
      const coordinates = features.flatMap((feature) => geometryCoordinates(feature.geometry).flat());
      const xs = coordinates.map((point) => point[0]);
      const ys = coordinates.map((point) => point[1]);
      const bounds = { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
      const width = 360;
      const height = 250;
      const selected = String(region || "ALL").toUpperCase();
      const selectedName = typeof evStateName === "function" ? evStateName(selected) : selected;
      const paths = features.map((feature) => {
        const code = String(feature.properties?.code || "").toUpperCase();
        const name = feature.properties?.name || code;
        const isSelected = selected === "ALL" || code === selected;
        return `<path class="forecast-map-state${isSelected ? " is-selected" : ""}" d="${featurePath(feature, bounds, width, height)}" tabindex="0" role="button" aria-label="${name}" data-state="${code}"><title>${name}</title></path>`;
      }).join("");
      const centerX = width / 2;
      const centerY = height / 2;
      mapEl.innerHTML = `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet" aria-hidden="true"><g transform="translate(${centerX} ${centerY}) scale(${mapZoom}) translate(${-centerX} ${-centerY})">${paths}</g></svg>`;
      valueEl.textContent = Number.isFinite(Number(value)) ? `${Number(value).toLocaleString("en-IN")} · ${period || "latest"}` : "Forecast ready";
      statusEl.textContent = selected === "ALL" ? `All India · ${target}` : `${selectedName} · ${target}`;
    } catch (error) {
      mapEl.innerHTML = "";
      valueEl.textContent = "Map unavailable";
      statusEl.textContent = error.message;
    }
  }

  function renderStaticChart(hist, fut) {
    const labels = [...hist.map((p) => p.year), ...fut.map((p) => p.year)];
    const histData = [...hist.map((p) => p.value), ...fut.map(() => null)];
    const futData = [...hist.map(() => null), ...fut.map((p) => p.value)];
    if (hist.length) futData[hist.length - 1] = hist[hist.length - 1].value;
    if (chart) chart.destroy();
    chart = new Chart(document.getElementById("forecastChart"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "History", data: histData, borderColor: "#2dd4bf", tension: 0.3, spanGaps: false },
          { label: "Forecast", data: futData, borderColor: "#38bdf8", borderDash: [6, 4], tension: 0.3, spanGaps: true },
        ],
      },
      options: {
        plugins: { legend: { labels: { color: "#cfe3ec" } } },
        scales: {
          x: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    });
  }

  function renderApiChart(out) {
    const hist = out.history || {};
    const fut = out.forecast || {};
    const histLabels = hist.dates || hist.years || [];
    const histVals = hist.values || hist.ev_sales || [];
    const futLabels = fut.dates || fut.years || (fut.points || []).map((p) => p.period || p.year);
    const futVals = fut.values || fut.ev_sales || (fut.points || []).map((p) => p.value);
    const labels = [...histLabels, ...futLabels];
    const histData = [...histVals, ...futLabels.map(() => null)];
    const futData = [...histLabels.map(() => null), ...futVals];
    if (histVals.length) futData[histVals.length - 1] = histVals[histVals.length - 1];
    if (chart) chart.destroy();
    chart = new Chart(document.getElementById("forecastChart"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "History", data: histData, borderColor: "#2dd4bf", tension: 0.3, spanGaps: false },
          { label: "Forecast", data: futData, borderColor: "#38bdf8", borderDash: [6, 4], tension: 0.3, spanGaps: true },
        ],
      },
      options: {
        plugins: { legend: { labels: { color: "#cfe3ec" } } },
        scales: {
          x: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    });
  }

  async function runStaticForecast() {
    const state = document.getElementById("predRegion").value;
    const vehicle = document.getElementById("predVehicle").value;
    const horizon = Number(document.getElementById("predHorizon").value);
    const annual = await EVPagesData.annual();
    const shap = await EVPagesData.shapImportance();
    const hist = EVPagesData.seriesFor(annual, state, vehicle);
    if (!hist.length) {
      throw new Error("No historical data is available for this selection.");
    }
    const fut = EVPagesData.forecast(hist, horizon);
    const expl = EVPagesData.explainSeries(hist, hist[hist.length - 1]?.year, shap);
    const name = typeof evStateName === "function" ? evStateName(state) : state;
    document.getElementById("predResult").innerHTML =
      `<strong>${name}</strong> · ${vehicle} · next ${horizon} year(s)<br>` +
      fut.map((p) => `${p.year}: ${p.value.toLocaleString()}`).join(" · ");
    document.getElementById("predXai").innerHTML =
      `<strong>Why (${name}):</strong> ${expl.growth_pct >= 0 ? "Increase" : "Decrease"} vs last year (${expl.growth_pct.toFixed(1)}%). ` +
      `Top positive: ${expl.pos[0]?.label || "—"}. Top negative: ${expl.neg[0]?.label || "none"}.`;
    renderStaticChart(hist, fut);
    const latest = fut[fut.length - 1];
    await renderForecastMap(state, document.getElementById("predTarget")?.value || "registrations", latest?.value, latest?.year);
  }

  async function runApiForecast() {
    const region = document.getElementById("predRegion").value;
    const vehicle = document.getElementById("predVehicle").value;
    const horizon = Number(document.getElementById("predHorizon").value);
    const target = document.getElementById("predTarget")?.value || "registrations";
    const resultEl = document.getElementById("predResult");
    resultEl.innerHTML = `<span class="text-muted-2">Loading forecast from saved models…</span>`;
    const out = await EVForecast.API.forecast(region, horizon, target, vehicle);
    if (!out.ok) {
      resultEl.innerHTML = `<div class="text-danger">${out.message || "Forecast failed"}</div>`;
      return;
    }
    const unit =
      target === "revenue" ? "revenue" : target === "transactions" ? "transactions" : "registrations";
    const points = (out.forecast?.points || []).map((p) => {
      const period = p.period || p.year;
      return `<li class="mb-1"><strong>${period}</strong> → ${Number(p.value).toLocaleString("en-IN")} ${unit}</li>`;
    }).join("");
    resultEl.innerHTML = `
      <div class="mb-2"><span class="chip">${out.region_name || region}</span>
      <span class="chip">${out.model || "Hybrid"}</span></div>
      <ul class="mb-0">${points}</ul>
      ${out.accuracy && out.accuracy.approx_accuracy != null
        ? `<p class="small mt-2 mb-0"><strong>Held-out accuracy:</strong> ${out.accuracy.approx_accuracy}% (${out.accuracy.best_model || "best RMSE"} · MAPE ${out.accuracy.MAPE != null ? Number(out.accuracy.MAPE).toFixed(1) : "—"}%)</p>`
        : ""}`;
    const drivers = out.top_factors || [];
    document.getElementById("predXai").innerHTML = drivers.length
      ? `<strong>Top factors:</strong> ${drivers.slice(0, 3).map((d) => d.label || d.feature).join(", ")}.`
      : "";
    renderApiChart(out);
    const latest = out.forecast?.points?.[out.forecast.points.length - 1] || {};
    await renderForecastMap(region, target, latest.value, latest.period || latest.year);
  }

  async function runForecast() {
    try {
      if (window.EVPages?.hasBackend) {
        await runApiForecast();
      } else {
        await runStaticForecast();
      }
    } catch (err) {
      console.warn("API forecast failed, using static:", err);
      await runStaticForecast();
    }
  }

  async function fillRegions() {
    const sel = document.getElementById("predRegion");
    if (window.EVPages?.hasBackend) {
      const regs = await EVForecast.API.regions();
      sel.innerHTML = (regs.regions || [])
        .map((r) => {
          if (typeof r === "string") {
            const name = typeof evStateName === "function" ? evStateName(r) : r;
            return `<option value="${r}">${name}</option>`;
          }
          return `<option value="${r.code}">${r.name}</option>`;
        })
        .join("");
      return;
    }
    const annual = await EVPagesData.annual();
    const states = [...new Set(annual.map((r) => r.state))].filter(Boolean).sort();
    sel.innerHTML =
      `<option value="ALL">All India</option>` +
      states
        .filter((s) => s !== "ALL")
        .map((s) => {
          const name = typeof evStateName === "function" ? evStateName(s) : s;
          return `<option value="${s}">${name}</option>`;
        })
        .join("");
  }

  window.EVStaticPages = window.EVStaticPages || {};
  window.EVStaticPages.initPrediction = async function () {
    await window.EVPages.ready;
    await fillRegions();
    document.getElementById("forecastMapZoomIn")?.addEventListener("click", () => {
      mapZoom = Math.min(3, Number((mapZoom + 0.25).toFixed(2)));
      renderForecastMap(document.getElementById("predRegion").value, document.getElementById("predTarget")?.value || "registrations");
    });
    document.getElementById("forecastMapZoomOut")?.addEventListener("click", () => {
      mapZoom = Math.max(1, Number((mapZoom - 0.25).toFixed(2)));
      renderForecastMap(document.getElementById("predRegion").value, document.getElementById("predTarget")?.value || "registrations");
    });
    document.getElementById("forecastMapZoomReset")?.addEventListener("click", () => {
      mapZoom = 1;
      renderForecastMap(document.getElementById("predRegion").value, document.getElementById("predTarget")?.value || "registrations");
    });
    document.getElementById("predForm").addEventListener("submit", (e) => {
      e.preventDefault();
      runForecast();
    });
  };
})();
