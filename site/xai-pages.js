(() => {
  const fmt = (n) =>
    n == null || !Number.isFinite(Number(n)) ? "—" : Math.round(Number(n)).toLocaleString("en-IN");
  const fmtPct = (n) =>
    n == null || !Number.isFinite(Number(n)) ? "—" : `${Number(n).toFixed(1)}%`;

  let annual = [];
  let importance = { ranking: [] };
  let nationalPack = null;
  let tsChart = null;
  let localChart = null;
  let impChart = null;

  const statePlaybooks = {
    "Andaman and Nicobar Islands": "island logistics, tourism fleets, and resilient charging", "Arunachal Pradesh": "mountain-route range confidence and dependable charging",
    "Andhra Pradesh": "fleet electrification and district-level dealer coverage", "Assam": "urban two-wheeler affordability and charging access", "Bihar": "entry-level financing and rural-to-urban distribution", "Delhi": "high-utilization fleets, air-quality policy, and charging reliability", "Goa": "tourism fleets and destination charging", "Gujarat": "manufacturing ecosystem, fleet demand, and fast-charging coverage", "Haryana": "NCR commuter demand, fleet operators, and workplace charging", "Karnataka": "technology-led adoption, workplace charging, and fleet pilots", "Kerala": "two-wheeler affordability, tourism fleets, and dense charging", "Maharashtra": "urban fleets, financing, and high-density public charging", "Punjab": "commercial mobility and highway charging", "Rajasthan": "long-distance range confidence and highway charging", "Tamil Nadu": "manufacturing supply, commuter adoption, and fleet scale-up", "Telangana": "Hyderabad fleet adoption and workplace charging", "Uttar Pradesh": "large-city and tier-two financing, supply, and charging", "West Bengal": "Kolkata fleet demand and regional charging coverage",
    "Chandigarh": "public and institutional fleet adoption", "Chhattisgarh": "industrial and commercial fleet conversion", "Dadra and Nagar Haveli and Daman and Diu": "industrial mobility and compact charging corridors", "Himachal Pradesh": "hill-route range confidence and resilient charging", "Jammu and Kashmir": "cold-weather range support and corridor charging", "Jharkhand": "industrial fleet demand and dealership reach", "Manipur": "urban mobility, two-wheeler affordability, and corridor charging", "Meghalaya": "hill mobility, tourism fleets, and weather-resilient charging", "Mizoram": "compact urban mobility and dependable hill-route charging", "Nagaland": "district distribution, fleet pilots, and corridor charging", "Odisha": "public transport electrification and coastal corridor coverage", "Puducherry": "tourism mobility, urban two-wheelers, and dense charging", "Sikkim": "mountain tourism fleets and reliable low-volume charging", "Tripura": "urban two-wheeler affordability and regional supply", "Uttarakhand": "hill mobility, tourism fleets, and reliable corridor charging", "Lakshadweep": "island logistics, tourism mobility, and resilient charging"
  };

  function factorAction(factor, stateName, positive) {
    const label = String(factor?.label || "").toLowerCase();
    const focus = statePlaybooks[stateName] || "local affordability, vehicle availability, fleet demand, and charging access";
    if (label.includes("year-over-year") || label.includes("growth rate") || label.includes("yoy")) return positive ? `Protect the acceleration through ${focus}.` : `Reverse the slowdown by prioritizing ${focus}.`;
    if (label.includes("rolling average")) return positive ? `Maintain consistent supply and service quality across ${focus}.` : `Stabilize supply and build consistent demand through ${focus}.`;
    if (label.includes("previous year") || label.includes("2 years ago") || label.includes("3 years ago") || label.includes("lag")) return positive ? `Retain repeat buyers and fleet customers while scaling ${focus}.` : `Recover the baseline with targeted offers, fleet outreach, and better ${focus}.`;
    if (label.includes("vehicle type")) return positive ? `Preserve segment availability and expand ${focus}.` : "Check segment pricing, model availability, financing, and dealer coverage.";
    if (label.includes("state") || label.includes("region")) return positive ? `Protect the advantage with continued investment in ${focus}.` : `Benchmark nearby markets and remove barriers affecting ${focus}.`;
    return positive ? `Monitor the feature and keep investing in ${focus}.` : `Inspect the feature trend and test a targeted response around ${focus}.`;
  }

  function factorGuidance(factors, heading, stateName, positive) {
    if (!factors?.length) return "";
    return `<p class="mt-3 mb-1"><strong>${heading}</strong></p><ul class="mb-2">${factors.slice(0, 3).map((factor) => {
      const action = factorAction(factor, stateName, positive);
      return `<li><strong>${factor.label}:</strong> ${positive ? "This factor supports the model direction." : "This factor is associated with downward pressure in the model."} <span class="text-muted-2">Suggested response: ${action}</span></li>`;
    }).join("")}</ul>`;
  }

  function paintGrowth(growth, pos, neg, accNote, stateName) {
    const el = document.getElementById("growthDirPanel");
    const gEl = document.getElementById("kpiGrowth");
    if (gEl) gEl.style.color = growth >= 0 ? "#6ee7b7" : "#fca5a5";
    if (!el) return;
    const row = (f, kind) =>
      `<li><strong>${f.label}</strong> — ${kind} share ${fmtPct(f.pct)}`
      + (f.actual_display ? ` · value ${f.actual_display}` : "")
      + `</li>`;
    let html = "";
    if (growth >= 0) {
      html += `<h2 class="h6" style="color:#6ee7b7">Prediction / growth is POSITIVE (${fmtPct(growth)})</h2>`;
      html += `<p>These factors <strong>made growth positive</strong> (share of the explanation):</p><ol>${pos.map((f) => row(f, "positive")).join("") || "<li>None</li>"}</ol>`;
      if (neg.length) {
        html += `<p>These factors worked <strong>against</strong> the rise:</p><ul>${neg.map((f) => row(f, "negative")).join("")}</ul>`;
      }
      html += factorGuidance(pos, `How ${stateName} can sustain and scale positive growth`, stateName, true);
    } else {
      html += `<h2 class="h6" style="color:#fca5a5">Prediction / growth is NEGATIVE (${fmtPct(growth)})</h2>`;
      html += `<p>These factors <strong>made growth negative</strong> (share of the explanation):</p><ol>${neg.map((f) => row(f, "negative")).join("") || "<li>None</li>"}</ol>`;
      if (pos.length) {
        html += `<p>These factors still <strong>supported</strong> the prediction:</p><ul>${pos.map((f) => row(f, "positive")).join("")}</ul>`;
      }
      html += factorGuidance(neg, `Why ${stateName} may be negative and how to improve`, stateName, false);
    }
    html += `<p class="mb-0"><strong>Accuracy:</strong> ${accNote}</p>`;
    el.innerHTML = html;
  }

  function stateName(code) {
    const pack = nationalPack?.filter_options?.regions || [];
    const hit = pack.find((r) => r.code === code);
    return hit ? hit.name : code;
  }

  function fillStates() {
    const codes = [...new Set(annual.map((r) => r.state).filter(Boolean))].sort();
    const sel = document.getElementById("xaiState");
    sel.innerHTML =
      `<option value="ALL">All India</option>` +
      codes.map((c) => `<option value="${c}">${typeof evStateName === "function" ? evStateName(c) : c}</option>`).join("");
  }

  function fillYears(hist) {
    const sel = document.getElementById("xaiYear");
    const years = hist.map((p) => p.year);
    sel.innerHTML = years.map((y) => `<option value="${y}">${y}</option>`).join("");
    if (years.length) sel.value = String(years[years.length - 1]);
  }

  function drawTS(hist, pred, fut) {
    const labels = [...hist.map((p) => p.year), ...fut.map((p) => p.year)];
    const actual = [...hist.map((p) => p.value), ...fut.map(() => null)];
    const predicted = hist.map((p, i) => (i === hist.length - 1 ? pred : null));
    while (predicted.length < labels.length) predicted.push(null);
    predicted[hist.length - 1] = pred;
    fut.forEach((p, i) => {
      predicted[hist.length + i] = p.value;
    });
    if (tsChart) tsChart.destroy();
    tsChart = new Chart(document.getElementById("chartTimeseries"), {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Actual",
            data: actual,
            borderColor: "#38bdf8",
            backgroundColor: "rgba(56,189,248,0.12)",
            fill: true,
            tension: 0.3,
            spanGaps: false,
          },
          {
            label: "Predicted / forecast",
            data: predicted,
            borderColor: "#f5b942",
            borderDash: [6, 4],
            tension: 0.3,
            spanGaps: true,
          },
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

  function drawLocal(contribs) {
    if (localChart) localChart.destroy();
    localChart = new Chart(document.getElementById("chartLocal"), {
      type: "bar",
      data: {
        labels: contribs.map((c) => c.label),
        datasets: [
          {
            label: "Contribution share %",
            data: contribs.map((c) => (c.direction === "negative" ? -c.pct : c.pct)),
            backgroundColor: contribs.map((c) =>
              c.direction === "negative" ? "rgba(252,165,165,0.7)" : "rgba(110,231,183,0.7)"
            ),
          },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#cfe3ec" }, grid: { display: false } },
        },
      },
    });
  }

  function drawImp() {
    const rank = importance.ranking || [];
    if (impChart) impChart.destroy();
    impChart = new Chart(document.getElementById("chartImportance"), {
      type: "bar",
      data: {
        labels: rank.map((r) => r.feature),
        datasets: [
          {
            label: "SHAP importance",
            data: rank.map((r) => r.importance),
            backgroundColor: "rgba(45,212,191,0.45)",
            borderColor: "#2dd4bf",
          },
        ],
      },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#cfe3ec" }, grid: { display: false } },
        },
      },
    });
  }

  function renderAccuracy() {
    const table = document.querySelector("#accuracyTable tbody");
    const note = document.getElementById("accuracyNote");
    if (!table) return;
    const accuracy = nationalPack?.accuracy || {};
    const models = accuracy.all_models || [];
    const best = accuracy.best_model;
    const explanation = accuracy.explanation_model || "Random Forest";
    if (note) {
      note.textContent = accuracy.label_approx ||
        "Approx. accuracy = max(0, 100 − MAPE) on held-out test years. SHAP explanations use Random Forest.";
    }
    table.innerHTML = models.length
      ? models.map((model) => {
          const tags = [];
          if (model.model === best) tags.push("best forecast");
          if (model.model === explanation || model.model === "Random Forest") tags.push("SHAP explanation");
          return `<tr><td>${model.model}${tags.length ? ` <span class="text-muted-2">(${tags.join(", ")})</span>` : ""}</td>`
            + `<td>${fmt(model.MAE)}</td><td>${fmt(model.RMSE)}</td>`
            + `<td>${fmtPct(model.MAPE)}</td><td>${model.R2 == null ? "—" : Number(model.R2).toFixed(3)}</td>`
            + `<td>${model.approx_accuracy == null ? "—" : fmtPct(model.approx_accuracy)}</td></tr>`;
        }).join("")
      : `<tr><td colspan="6" class="text-muted-2">Accuracy details are not available for this selection.</td></tr>`;
  }

  function fromNationalPack() {
    const k = nationalPack.kpis || {};
    const ch = nationalPack.charts?.timeseries || {};
    const loc = nationalPack.local_explanation || {};
    const selectedState = nationalPack.filters?.state_name || stateName(nationalPack.filters?.state) || "the selected region";
    const contribs = (loc.all_contributions || []).map((c) => ({
      feature: c.feature,
      label: c.label,
      contribution: c.contribution,
      pct: c.pct,
      direction: c.direction,
      actual_display: c.actual_display,
    }));
    document.getElementById("kpiCurrent").textContent = fmt(k.current_sales);
    document.getElementById("kpiPred").textContent = fmt(k.predicted_sales);
    document.getElementById("kpiGrowth").textContent = fmtPct(k.growth_pct);
    document.getElementById("kpiPos").textContent = k.top_positive_factor || "—";
    document.getElementById("kpiNeg").textContent = k.top_negative_factor || "—";
    const accEl = document.getElementById("kpiAcc");
    if (accEl) {
      accEl.textContent = k.explanation_model_accuracy_approx != null
        ? `${k.explanation_model_accuracy_approx}%`
        : (k.forecast_accuracy_approx != null ? `${k.forecast_accuracy_approx}%` : "—");
    }
    const rf = k.explanation_model_accuracy_approx;
    const best = k.forecast_accuracy_approx;
    const pe = nationalPack.accuracy?.point_forecast_error?.abs_pct_error;
    paintGrowth(
      Number(k.growth_pct),
      loc.positive_contributors || [],
      loc.negative_contributors || [],
      `Random Forest (SHAP) ${rf != null ? rf + "%" : "—"} · best forecast model ${best != null ? best + "%" : "—"}`
        + (pe != null ? ` · this point absolute error ${Number(pe).toFixed(1)}%` : "")
        + `. This is a regression evaluation proxy, not confidence; verified 98% performance would require held-out validation.`
      , selectedState
    );
    const nl = loc.natural_language || {};
    document.getElementById("predCard").innerHTML =
      `<p>${nl.overall || nationalPack.explanation_panel?.main_reason || ""}</p>` +
      `<p class="mb-0">${nl.causality_note || nationalPack.disclaimer || ""}</p>`;
    document.getElementById("localExplainSummary").textContent = nl.summary || "";
    renderAccuracy();
    const dates = (ch.dates || []).map(Number);
    const actual = ch.actual || [];
    const hist = dates.map((y, i) => ({ year: y, value: actual[i] })).filter((p) => Number.isFinite(p.value));
    const pred = k.predicted_sales;
    const fut = (ch.forecast_dates || []).map((y, i) => ({ year: Number(y), value: (ch.forecast || [])[i] }));
    drawTS(hist, pred, fut.filter((p) => Number.isFinite(p.value)));
    drawLocal(contribs);
    document.querySelector("#contribTable tbody").innerHTML = contribs
      .map(
        (c) =>
          `<tr><td>${c.label}</td><td>${c.actual_display || "—"}</td><td>${fmtPct(c.pct)}</td><td>${c.direction}</td></tr>`
      )
      .join("");
    document.getElementById("posDrivers").innerHTML = (loc.positive_contributors || [])
      .map((c) => `<li><span>${c.label}</span><span class="pos">${fmtPct(c.pct)}</span></li>`)
      .join("");
    document.getElementById("negDrivers").innerHTML = (loc.negative_contributors || [])
      .map((c) => `<li><span>${c.label}</span><span class="neg">${fmtPct(c.pct)}</span></li>`)
      .join("");
    renderExternalDrivers(nationalPack.external_drivers);
  }

  function renderExternalDrivers(drivers) {
    const el = document.getElementById("externalDriversGrid");
    if (!el) return;
    if (drivers && drivers.length) {
      el.innerHTML = drivers.map((d) => `
        <div class="col-sm-6 col-lg-4">
          <div class="glass p-3 h-100 xai-driver-card" style="border:1px solid rgba(45,212,191,0.18);border-radius:12px">
            <div class="d-flex justify-content-between align-items-center mb-2">
              <span class="fs-4">${d.icon || "📊"}</span>
              <span class="badge" style="background:rgba(45,212,191,0.15);color:#2dd4bf;border:1px solid rgba(45,212,191,0.3)">Active Driver</span>
            </div>
            <div class="text-muted-2 small fw-semibold">${d.label}</div>
            <div class="h5 my-1 text-info fw-bold">${d.display || d.value}</div>
            <div class="small text-muted-2 mt-1">${d.description || ""}</div>
          </div>
        </div>
      `).join("");
    }
  }

  function renderComputed() {
    const state = document.getElementById("xaiState").value;
    const vehicle = document.getElementById("xaiVehicle").value;
    const hist = EVPagesData.seriesFor(annual, state, vehicle);
    if (!hist.length) return;
    const yearSel = document.getElementById("xaiYear");
    if (![...yearSel.options].some((o) => o.value === yearSel.value)) fillYears(hist);
    const year = Number(yearSel.value);
    const expl = EVPagesData.explainSeries(hist, year, importance);
    document.getElementById("kpiCurrent").textContent = fmt(expl.current);
    document.getElementById("kpiPred").textContent = fmt(expl.predicted);
    document.getElementById("kpiGrowth").textContent = fmtPct(expl.growth_pct);
    document.getElementById("kpiPos").textContent = expl.pos[0]?.label || "—";
    document.getElementById("kpiNeg").textContent = expl.neg[0]?.label || "—";
    const accEl = document.getElementById("kpiAcc");
    const rf = nationalPack?.kpis?.explanation_model_accuracy_approx;
    if (accEl) accEl.textContent = rf != null ? `${rf}%` : "—";
    paintGrowth(
      expl.growth_pct,
      expl.pos,
      expl.neg,
      `Factor shares are SHAP-style weights for this state/year. Explanation-model accuracy ${rf != null ? rf + "%" : "not loaded"} is a regression proxy (100 − MAPE), not confidence.`,
      state === "ALL" ? "All India" : (typeof evStateName === "function" ? evStateName(state) : state)
    );
    renderAccuracy();
    const dir = expl.growth_pct >= 0 ? "increase" : "decrease";
    document.getElementById("predCard").innerHTML =
      `<p>For <strong>${state === "ALL" ? "All India" : (typeof evStateName === "function" ? evStateName(state) : state)}</strong> in ${expl.year}, registrations ${dir} ` +
      `${fmtPct(Math.abs(expl.growth_pct))} vs the previous year.</p>` +
      `<p class="mb-0">Main lift: ${expl.pos[0]?.label || "trend features"}. Main drag: ${expl.neg[0]?.label || "none"}.</p>`;
    document.getElementById("localExplainSummary").textContent =
      `Local explanation uses SHAP global weights on lag_1, lag_2, lag_3, 3-year average, YoY, and Year.`;
    drawTS(hist, expl.predicted, expl.forecast);
    drawLocal(expl.contribs);
    document.querySelector("#contribTable tbody").innerHTML = expl.contribs
      .map(
        (c) =>
          `<tr><td>${c.label}</td><td>${c.actual_display}</td><td>${fmtPct(c.pct)}</td><td>${c.direction}</td></tr>`
      )
      .join("");
    document.getElementById("posDrivers").innerHTML = expl.pos
      .slice(0, 5)
      .map((c) => `<li><span>${c.label}</span><span class="pos">${fmtPct(c.pct)}</span></li>`)
      .join("");
    document.getElementById("negDrivers").innerHTML = expl.neg.length
      ? expl.neg
          .slice(0, 5)
          .map((c) => `<li><span>${c.label}</span><span class="neg">${fmtPct(c.pct)}</span></li>`)
          .join("")
      : `<li class="text-muted-2">No negative drivers for this slice.</li>`;
  }

  async function refreshFromApi() {
    const state = document.getElementById("xaiState").value;
    const vehicle = document.getElementById("xaiVehicle").value;
    const year = document.getElementById("xaiYear").value;
    const pack = await EVForecast.API.xaiDashboard({ region: state, vehicle_type: vehicle, year });
    nationalPack = pack;
    fromNationalPack();
  }

  async function refresh() {
    const state = document.getElementById("xaiState").value;
    const badge = document.getElementById("xaiStateBadge");
    if (badge) badge.textContent = typeof evStateName === "function" ? evStateName(state) : (state === "ALL" ? "All India" : state);

    if (window.EVPages?.hasBackend) {
      try {
        await refreshFromApi();
        return;
      } catch (err) {
        console.warn("XAI API failed, using static computation:", err);
      }
    }

    const vehicle = document.getElementById("xaiVehicle").value;
    const year = Number(document.getElementById("xaiYear").value);
    const hist = EVPagesData.seriesFor(annual, state, vehicle);
    fillYears(hist);
    if (year && [...document.getElementById("xaiYear").options].some((o) => Number(o.value) === year)) {
      document.getElementById("xaiYear").value = String(year);
    }
    const usePack =
      nationalPack &&
      state === "ALL" &&
      vehicle === "All" &&
      Number(document.getElementById("xaiYear").value) === 2024;
    if (usePack) fromNationalPack();
    else renderComputed();
  }

  document.getElementById("xaiState").addEventListener("change", refresh);
  document.getElementById("xaiYear").addEventListener("change", refresh);
  document.getElementById("xaiVehicle").addEventListener("change", refresh);

  (async () => {
    await window.EVPages.ready;
    annual = await EVPagesData.annual();
    importance = await EVPagesData.shapImportance();
    try {
      nationalPack = EVPages.hasBackend
        ? await EVForecast.API.xaiDashboard({ region: "ALL", vehicle_type: "All" })
        : await EVPagesData.nationalXai();
    } catch (_) {
      nationalPack = null;
    }
    fillStates();
    fillYears(EVPagesData.seriesFor(annual, "ALL", "All"));
    renderAccuracy();
    drawImp();
    refresh();
  })();
})();
