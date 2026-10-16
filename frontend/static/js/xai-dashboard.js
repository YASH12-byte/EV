(() => {
  const fmt = (n) => (n == null || Number.isNaN(Number(n)) ? "—" : Math.round(Number(n)).toLocaleString("en-IN"));
  const fmtPct = (n) => (n == null || !Number.isFinite(Number(n)) ? "—" : `${Number(n).toFixed(1)}%`);
  let impChart = null;
  let filters = { state: "ALL", year: "", vehicle_type: "All" };
  let loadTimer = null;
  let loadSeq = 0;
  let filtersReady = false;
  let activeRequest = null;
  let chartTimer = null;
  let secondaryChartTimer = null;
  let localChartTimer = null;
  const responseCache = new Map();

  function toast(msg, ok = true) {
    const el = document.getElementById("xaiToast");
    el.textContent = msg;
    el.className = `xai-toast ${ok ? "ok" : "err"}`;
    el.classList.remove("d-none");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add("d-none"), 4500);
  }

  function fmtMetric(n, digits = 1) {
    if (n == null || !Number.isFinite(Number(n))) return "—";
    return Number(n).toLocaleString("en-IN", { maximumFractionDigits: digits });
  }

  function renderAccuracy(acc, kpis) {
    const label = acc?.label_approx || "Approx. forecast accuracy = max(0, 100 − MAPE) on held-out test years.";
    document.getElementById("accLabel").textContent = label;

    const rows = acc?.all_models || [];
    const best = acc?.best_model;
    const expl = acc?.explanation_model || "RandomForest";
    document.querySelector("#accTable tbody").innerHTML = rows.length
      ? rows.map((r) => {
          const tags = [];
          if (r.model === best) tags.push("best RMSE");
          if (r.model === expl || r.model === "Random Forest") tags.push("SHAP");
          const tag = tags.length ? ` <span class="text-muted-2">(${tags.join(", ")})</span>` : "";
          return `<tr>
            <td>${r.model}${tag}</td>
            <td>${fmtMetric(r.MAE, 0)}</td>
            <td>${fmtMetric(r.RMSE, 0)}</td>
            <td>${r.MAPE != null ? `${fmtMetric(r.MAPE)}%` : "—"}</td>
            <td>${r.R2 != null ? fmtMetric(r.R2, 3) : "—"}</td>
            <td>${r.approx_accuracy != null ? `${r.approx_accuracy}%` : "—"}</td>
          </tr>`;
        }).join("")
      : `<tr><td colspan="6" class="text-muted-2">Run python run_project.py to generate evaluation metrics.</td></tr>`;

    const pe = acc?.point_forecast_error;
    const peEl = document.getElementById("pointErr");
    if (pe && kpis?.current_sales != null && kpis?.predicted_sales != null) {
      peEl.textContent = `Point forecast for selection: actual ${fmt(kpis.current_sales)}, predicted ${fmt(kpis.predicted_sales)}`
        + (pe.abs_pct_error != null ? ` — absolute error ${fmtMetric(pe.abs_pct_error)}%.` : ".");
    } else {
      peEl.textContent = "";
    }
  }

  function setLoading(on) {
    document.getElementById("xaiSpin").classList.toggle("d-none", !on);
    document.getElementById("xaiRefresh").disabled = on;
  }

  function fillSelect(id, options, valueKey, labelKey, selected) {
    const sel = document.getElementById(id);
    sel.innerHTML = "";
    (options || []).forEach((o) => {
      const opt = document.createElement("option");
      if (typeof o === "object") {
        opt.value = o[valueKey];
        opt.textContent = o[labelKey];
      } else {
        opt.value = o;
        opt.textContent = o;
      }
      sel.appendChild(opt);
    });
    if (selected != null) sel.value = selected;
  }

  const statePlaybooks = {
    "Andaman and Nicobar Islands": "island logistics, tourism fleets, and resilient charging",
    "Andhra Pradesh": "fleet electrification and district-level dealer coverage",
    "Arunachal Pradesh": "mountain-route range confidence and dependable charging",
    "Assam": "urban two-wheeler affordability and charging access",
    "Bihar": "entry-level financing and rural-to-urban distribution",
    "Chandigarh": "public and institutional fleet adoption",
    "Chhattisgarh": "industrial and commercial fleet conversion",
    "Dadra and Nagar Haveli and Daman and Diu": "industrial mobility and compact charging corridors",
    "Delhi": "high-utilization fleets, air-quality policy, and charging reliability",
    "Goa": "tourism fleets and reliable destination charging",
    "Gujarat": "manufacturing ecosystem, fleet demand, and fast-charging coverage",
    "Haryana": "NCR commuter demand, fleet operators, and workplace charging",
    "Himachal Pradesh": "hill-route range confidence and resilient charging",
    "Jammu and Kashmir": "cold-weather range support and corridor charging",
    "Jharkhand": "industrial fleet demand and dealership reach",
    "Karnataka": "technology-led adoption, workplace charging, and fleet pilots",
    "Kerala": "two-wheeler affordability, tourism fleets, and dense charging",
    "Madhya Pradesh": "inter-city corridors and district-level availability",
    "Maharashtra": "urban fleets, financing, and high-density public charging",
    "Manipur": "urban mobility, two-wheeler affordability, and corridor charging",
    "Meghalaya": "hill mobility, tourism fleets, and weather-resilient charging",
    "Mizoram": "compact urban mobility and dependable hill-route charging",
    "Nagaland": "district distribution, fleet pilots, and corridor charging",
    "Odisha": "public transport electrification and coastal corridor coverage",
    "Puducherry": "tourism mobility, urban two-wheelers, and dense charging",
    "Punjab": "agri-linked commercial mobility and highway charging",
    "Rajasthan": "long-distance range confidence and highway charging",
    "Sikkim": "mountain tourism fleets and reliable low-volume charging",
    "Tamil Nadu": "manufacturing supply, commuter adoption, and fleet scale-up",
    "Telangana": "Hyderabad fleet adoption and workplace charging",
    "Tripura": "urban two-wheeler affordability and regional supply",
    "Uttar Pradesh": "large-city and tier-two financing, supply, and charging",
    "Uttarakhand": "hill mobility, tourism fleets, and reliable corridor charging",
    "West Bengal": "Kolkata fleet demand and regional charging coverage",
    "Lakshadweep": "island logistics, tourism mobility, and resilient charging",
  };

  function factorAction(factor, stateName, positive) {
    const label = String(factor?.label || factor?.feature || "").toLowerCase();
    const focus = statePlaybooks[stateName] || "local affordability, vehicle availability, fleet demand, and charging access";
    if (label.includes("year-over-year") || label.includes("growth rate") || label.includes("yoy")) {
      return {
        reason: positive ? "The latest period is accelerating against the previous period." : "The latest period is growing more slowly than the previous period.",
        action: positive ? `Protect this momentum through ${focus}.` : `Reverse the slowdown by prioritizing ${focus}.`
      };
    }
    if (label.includes("rolling average")) {
      return {
        reason: positive ? "The recent multi-year average confirms sustained demand." : "The recent multi-year average is weak or was pulled down by earlier slow periods.",
        action: positive ? `Maintain consistent supply and service quality across ${focus}.` : `Stabilize supply and build consistent demand through ${focus}.`
      };
    }
    if (label.includes("previous year") || label.includes("2 years ago") || label.includes("3 years ago") || label.includes("lag")) {
      return {
        reason: positive ? "Recent historical registrations provide a strong demand baseline." : "Recent historical registrations provide a lower comparison baseline for this prediction.",
        action: positive ? `Retain repeat buyers and fleet customers while scaling ${focus}.` : `Recover the baseline with targeted offers, fleet outreach, and better ${focus}.`
      };
    }
    if (label.includes("vehicle type")) {
      return {
        reason: positive ? "The selected vehicle segment is showing stronger learned demand in this slice." : "The selected vehicle segment has weaker historical demand in this slice.",
        action: positive ? `Preserve segment availability and expand ${focus}.` : "Check segment-specific pricing, model availability, financing, and dealer coverage."
      };
    }
    if (label.includes("state") || label.includes("region")) {
      return {
        reason: positive ? `The selected region has a stronger learned pattern for ${focus}.` : `The selected region has a lower learned pattern for ${focus}.`,
        action: positive ? `Protect the advantage with continued investment in ${focus}.` : `Benchmark nearby markets and remove barriers affecting ${focus}.`
      };
    }
    return {
      reason: positive ? "This feature value is associated with a higher prediction in the trained model for this selection." : "This feature value is associated with a lower prediction in the trained model for this selection.",
      action: positive ? `Monitor the feature and keep investing in ${focus}.` : `Inspect the feature trend and test a targeted response around ${focus}.`
    };
  }

  function factorGuidance(factors, heading, stateName, positive) {
    if (!factors?.length) return "";
    return `<p class="mt-3 mb-1"><strong>${heading}</strong></p><ul class="mb-2">${factors.slice(0, 3).map((factor) => {
      const guidance = factorAction(factor, stateName, positive);
      return `<li><strong>${factor.label || factor.feature}:</strong> ${guidance.reason} <span class="text-muted-2">Suggested response: ${guidance.action}</span></li>`;
    }).join("")}</ul>`;
  }

  function renderGrowthDirection(data) {
    const el = document.getElementById("growthDirPanel");
    if (!el) return;
    const k = data.kpis || {};
    const acc = data.accuracy || {};
    const loc = data.local_explanation || {};
    const growth = Number(k.growth_pct);
    const positive = loc.positive_contributors || data.explanation_panel?.positive_contributors || [];
    const negative = loc.negative_contributors || data.explanation_panel?.negative_contributors || [];
    const stateName = data.filters?.state_name || "the selected region";
    const rfAcc = k.explanation_model_accuracy_approx ?? acc.explanation_model_metrics?.approx_accuracy;
    const bestAcc = k.forecast_accuracy_approx ?? acc.best_model_metrics?.approx_accuracy;
    const pointErr = acc.point_forecast_error?.abs_pct_error;
    const growthEl = document.getElementById("kpiGrowth");
    if (growthEl) {
      growthEl.style.color = !Number.isFinite(growth) ? "" : growth >= 0 ? "#6ee7b7" : "#fca5a5";
    }
    const factorRow = (f) => {
      const share = f.pct != null ? fmtPct(f.pct) : "—";
      return `<li><strong>${f.label || f.feature}</strong> — contribution share ${share}`
        + (f.actual_display ? ` · value ${f.actual_display}` : "")
        + (rfAcc != null ? ` · explanation-model accuracy ${rfAcc}%` : "")
        + `</li>`;
    };
    if (!Number.isFinite(growth)) {
      el.innerHTML = "<p class='mb-0'>Growth is not available for this filter.</p>";
      return;
    }
    let html = "";
    if (growth >= 0) {
      html += `<h2 class="h6 text-success">Prediction / growth is POSITIVE (${fmtPct(growth)})</h2>`;
      html += `<p>These factors <strong>pushed the forecast up</strong> (local SHAP share of the explanation):</p><ol>`;
      html += positive.length ? positive.map(factorRow).join("") : "<li>No positive SHAP drivers for this slice.</li>";
      html += `</ol>`;
      if (negative.length) {
        html += `<p class="mt-2">Factors that still <strong>reduced</strong> the prediction (offset some of the rise):</p><ul class="mb-2">`;
        html += negative.map(factorRow).join("");
        html += `</ul>`;
      }
      html += factorGuidance(positive, `How ${stateName} can sustain and scale positive growth`, stateName, true);
    } else {
      html += `<h2 class="h6 text-danger">Prediction / growth is NEGATIVE (${fmtPct(growth)})</h2>`;
      html += `<p>These factors <strong>pulled the forecast down</strong> (local SHAP share of the explanation):</p><ol>`;
      html += negative.length ? negative.map(factorRow).join("") : "<li>No negative SHAP drivers for this slice.</li>";
      html += `</ol>`;
      if (positive.length) {
        html += `<p class="mt-2">Factors that still <strong>supported</strong> the prediction (limited the fall):</p><ul class="mb-2">`;
        html += positive.map(factorRow).join("");
        html += `</ul>`;
      }
      html += factorGuidance(negative, `Why ${stateName} may be negative and how to improve`, stateName, false);
    }
    html += `<p class="mb-0"><strong>Evaluation:</strong> forecast model ${bestAcc != null ? bestAcc + "%" : "—"} and explanation model proxy ${rfAcc != null ? rfAcc + "%" : "—"} (100 − MAPE, not confidence).`;
    html += pointErr != null ? ` · this point’s absolute error ${fmtMetric(pointErr)}%.` : ".";
    html += ` A 98% result should only be displayed after verified held-out evaluation; SHAP explains model behavior, not causation.</p>`;
    el.innerHTML = html;
  }

  function renderDrivers(listId, items, cls) {
    document.getElementById(listId).innerHTML = (items || []).length
      ? items.map((i) =>
          `<li><span>${i.label || i.feature}</span><span class="${cls}">${i.pct != null ? fmtPct(i.pct) : ""}</span></li>`
        ).join("")
      : `<li class="text-muted-2">None identified for this selection.</li>`;
  }

  function plotTimeseries(ch) {
    const traces = [];
    const dates = ch.dates || [];
    const actual = (ch.actual || []).map((v) => (v == null || !Number.isFinite(Number(v)) ? null : Number(v)));
    const predicted = (ch.predicted || []).map((v) => (v == null || !Number.isFinite(Number(v)) ? null : Number(v)));

    if (dates.length && actual.some((v) => v != null)) {
      traces.push({
        x: dates, y: actual, name: "Actual", mode: "lines+markers",
        line: { color: "#38bdf8", width: 2 },
        connectgaps: false,
        hovertemplate: "<b>%{x}</b><br>Actual: %{y:,.0f}<extra></extra>",
      });
    }
    if (dates.length && predicted.some((v) => v != null)) {
      traces.push({
        x: dates, y: predicted, name: "Predicted (RF test)", mode: "lines+markers",
        line: { color: "#a78bfa", dash: "dot", width: 2 },
        connectgaps: false,
        hovertemplate: "<b>%{x}</b><br>Predicted: %{y:,.0f}<extra></extra>",
      });
    }
    if (ch.forecast_dates?.length && ch.forecast?.length) {
      traces.push({
        x: ch.forecast_dates, y: ch.forecast, name: "Forecast", mode: "lines+markers",
        line: { color: "#2dd4bf", width: 3 },
      });
      if (ch.lower?.length) {
        traces.push({
          x: ch.forecast_dates, y: ch.upper, name: "Upper bound", mode: "lines",
          line: { width: 0 }, showlegend: false,
        });
        traces.push({
          x: ch.forecast_dates, y: ch.lower, name: "Confidence band", mode: "lines",
          fill: "tonexty", fillcolor: "rgba(45,212,191,0.15)", line: { width: 0 },
        });
      }
    }
    Plotly.newPlot("chartTimeseries", traces, {
      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
      font: { color: "#cfe3ec", family: "Outfit" },
      margin: { t: 20, r: 10, b: 48, l: 64 },
      legend: { orientation: "h" },
      xaxis: { title: "Year", gridcolor: "rgba(255,255,255,0.05)", tickangle: -25 },
      yaxis: { title: "EV Registrations", gridcolor: "rgba(255,255,255,0.05)", tickformat: ",.0f" },
      hovermode: "x unified",
    }, { responsive: true, displayModeBar: true });
  }

  function plotLocalContrib(wf) {
    const el = "chartLocalContrib";
    if (!wf?.contributions?.length) {
      Plotly.purge(el);
      return;
    }
    const labels = ["Baseline", ...wf.contributions.map((c) => c.label), "Final"];
    const measures = ["absolute", ...wf.contributions.map(() => "relative"), "total"];
    const values = [wf.base || 0, ...wf.contributions.map((c) => c.value), wf.final || 0];
    Plotly.newPlot(el, [{
      type: "waterfall", orientation: "v", x: labels, y: values, measure: measures,
      increasing: { marker: { color: "#2dd4bf" } },
      decreasing: { marker: { color: "#f87171" } },
      totals: { marker: { color: "#38bdf8" } },
      connector: { line: { color: "rgba(255,255,255,0.2)" } },
    }], {
      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
      font: { color: "#cfe3ec", size: 10 },
      margin: { t: 16, r: 10, b: 90, l: 55 },
      xaxis: { tickangle: -35 },
      yaxis: { title: "Registrations", tickformat: ",.0f" },
    }, { responsive: true, displayModeBar: false });
  }

  function renderLocalExplain(local, ex) {
    const box = document.getElementById("localExplainSummary");
    const tbody = document.querySelector("#contribTable tbody");
    if (!local?.ok) {
      box.innerHTML = `<div class="text-warning">${local?.error || ex?.main_reason || "Local explanation unavailable."}</div>`;
      if (tbody) tbody.innerHTML = "";
      Plotly.purge("chartLocalContrib");
      return;
    }
    const nl = ex?.natural_language || local?.natural_language || {};
    box.innerHTML = `
      <p><strong>Prediction:</strong> ${fmt(local.prediction)} · <strong>Baseline:</strong> ${fmt(local.baseline)} · <strong>Direction:</strong> ${local.direction || "—"}</p>
      <p class="mb-1">${nl.summary || ""}</p>
      <p class="mb-0">${nl.overall || ""}</p>
      <p class="small text-muted-2 mt-2 mb-0">${nl.causality_note || ""}${local.aggregate_note ? " " + local.aggregate_note : ""}</p>`;
    const contribs = local.all_contributions || [];
    if (tbody) {
      tbody.innerHTML = contribs.map((c) =>
        `<tr><td>${c.label || c.feature}</td><td>${c.actual_display || "—"}</td><td>${c.reference_display || "—"}</td>` +
        `<td>${c.shap_value >= 0 ? "+" : "−"}${Math.abs(Math.round(c.shap_value)).toLocaleString("en-IN")}</td>` +
        `<td>${c.direction || "—"}</td></tr>`
      ).join("");
    }
    clearTimeout(localChartTimer);
  }

  function plotWaterfall(wf) {
    if (!wf?.contributions?.length) {
      Plotly.purge("chartWaterfall");
      return;
    }
    const labels = ["Base", ...wf.contributions.map((c) => c.label), "Final"];
    const measures = ["absolute", ...wf.contributions.map(() => "relative"), "total"];
    const values = [wf.base || 0, ...wf.contributions.map((c) => c.value), wf.final || 0];
    Plotly.newPlot("chartWaterfall", [{
      type: "waterfall", orientation: "v", x: labels, y: values, measure: measures,
      connector: { line: { color: "rgba(255,255,255,0.2)" } },
      increasing: { marker: { color: "#2dd4bf" } },
      decreasing: { marker: { color: "#f87171" } },
      totals: { marker: { color: "#38bdf8" } },
    }], {
      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
      font: { color: "#cfe3ec", size: 11 },
      margin: { t: 20, r: 10, b: 80, l: 50 },
      xaxis: { tickangle: -35 },
    }, { responsive: true, displayModeBar: false });
  }

  function plotDependence(dep) {
    if (!dep?.x?.length) {
      Plotly.purge("chartDependence");
      return;
    }
    Plotly.newPlot("chartDependence", [{
      x: dep.x, y: dep.y, mode: "markers", type: "scatter",
      marker: { color: "#38bdf8", size: 6, opacity: 0.7 },
      name: dep.label,
    }], {
      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
      font: { color: "#cfe3ec" },
      margin: { t: 20, r: 10, b: 40, l: 50 },
      xaxis: { title: dep.label, gridcolor: "rgba(255,255,255,0.05)" },
      yaxis: { title: "Registrations", gridcolor: "rgba(255,255,255,0.05)" },
    }, { responsive: true, displayModeBar: false });
  }

  function plotPosNeg(pos, neg) {
    const labels = [...(pos || []).slice(0, 5).map((p) => p.label), ...(neg || []).slice(0, 5).map((n) => n.label)];
    const values = [
      ...(pos || []).slice(0, 5).map((p) => Math.abs(p.shap_value || p.pct || 0)),
      ...(neg || []).slice(0, 5).map((n) => -Math.abs(n.shap_value || n.pct || 0)),
    ];
    const colors = values.map((v) => (v >= 0 ? "#2dd4bf" : "#f87171"));
    Plotly.newPlot("chartPosNeg", [{
      x: labels, y: values, type: "bar", marker: { color: colors },
    }], {
      paper_bgcolor: "transparent", plot_bgcolor: "transparent",
      font: { color: "#cfe3ec", size: 10 },
      margin: { t: 20, r: 10, b: 90, l: 50 },
      xaxis: { tickangle: -35 },
      yaxis: { title: "Contribution", gridcolor: "rgba(255,255,255,0.05)" },
    }, { responsive: true, displayModeBar: false });
  }

  function plotImportance(ranking) {
    const top = (ranking || []).slice(0, 10);
    const labels = top.map((r) => r.label || r.feature);
    const values = top.map((r) => r.importance);
    if (impChart) impChart.destroy();
    impChart = new Chart(document.getElementById("chartImportance"), {
      type: "bar",
      data: { labels, datasets: [{ data: values, backgroundColor: "#2dd4bf" }] },
      options: {
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#8fa3b0" }, grid: { display: false } },
        },
      },
    });
    document.querySelector("#impTable tbody").innerHTML = top.map((r) =>
      `<tr><td>${r.label || r.feature}</td><td>${Number(r.importance).toFixed(2)}</td><td>${r.impact || "—"}</td></tr>`
    ).join("");
  }

  function applyData(data) {
    if (!data.ok) throw new Error(data.message || "XAI load failed");

    document.getElementById("xaiDisclaimer").textContent = data.disclaimer || "";
    document.getElementById("xaiLastRef").textContent = new Date(data.refreshed_at).toLocaleString();

    const k = data.kpis || {};
    const stateName = data.filters?.state_name || (window.evStateName ? evStateName(data.filters?.state) : data.filters?.state) || "All India";
    const badge = document.getElementById("xaiStateBadge");
    if (badge) badge.textContent = stateName;
    const tsTitle = document.getElementById("tsTitle");
    if (tsTitle) tsTitle.textContent = `${stateName} — Actual · Predicted · Forecast`;
    document.getElementById("kpiCurrent").textContent = fmt(k.current_sales);
    document.getElementById("kpiPred").textContent = fmt(k.predicted_sales);
    document.getElementById("kpiGrowth").textContent = fmtPct(k.growth_pct);
    document.getElementById("kpiAcc").textContent = k.explanation_model_accuracy_approx != null
      ? `${k.explanation_model_accuracy_approx}% (RF, 100 − MAPE)` : (k.forecast_accuracy_approx != null
      ? `${k.forecast_accuracy_approx}% (best model)` : "—");
    document.getElementById("kpiPos").textContent = k.top_positive_factor || "—";
    document.getElementById("kpiNeg").textContent = k.top_negative_factor || "—";
    renderGrowthDirection(data);

    const pc = data.prediction_card || {};
    const acc = data.accuracy || {};
    const accBest = acc.best_model_metrics || {};
    document.getElementById("predCard").innerHTML = `
      <p><strong>State:</strong> ${stateName}</p>
      <p><strong>Predicted EV Sales:</strong> ${fmt(pc.predicted_ev_sales)}</p>
      <p><strong>Previous Period:</strong> ${fmt(pc.previous_period_sales)}</p>
      <p><strong>Expected Growth:</strong> ${fmtPct(pc.expected_growth_pct)}</p>
      <p><strong>Direction:</strong> ${pc.direction || "—"} · <strong>Trend:</strong> ${pc.overall_trend || "—"}</p>
      <p><strong>Main + factor:</strong> ${pc.main_positive_factor || "—"}</p>
      <p><strong>Main − factor:</strong> ${pc.main_negative_factor || "—"}</p>
      <p><strong>Test-set accuracy:</strong> ${accBest.approx_accuracy != null ? accBest.approx_accuracy + "%" : "—"}
        (${acc.best_model || "best RMSE"} · MAPE ${accBest.MAPE != null ? Number(accBest.MAPE).toFixed(1) + "%" : "—"})</p>
      <p class="mb-0"><strong>Interval:</strong> ${fmt(pc.confidence?.lower)} – ${fmt(pc.confidence?.upper)}<br/>
      <span class="text-muted-2">${pc.confidence?.note || ""}</span></p>`;

    const ex = data.explanation_panel || {};
    const nl = ex.natural_language || {};
    document.getElementById("whyPanel").innerHTML = `
      <p><strong>Trend:</strong> ${ex.trend || "—"} · <strong>Change:</strong> ${fmtPct(ex.change_pct)}</p>
      <p><strong>Main reason:</strong> ${ex.main_reason || nl.overall || "—"}</p>
      <p><strong>Positive contributors:</strong></p>
      <ol>${(nl.main_reasons || []).map((l) => `<li>${l}</li>`).join("") || "<li>—</li>"}</ol>
      <p><strong>Factors reducing prediction:</strong></p>
      <ol class="mb-2">${(nl.reducing_factors || []).map((l) => `<li>${l}</li>`).join("") || "<li>None</li>"}</ol>
      <p class="mb-0"><strong>Model interpretation:</strong> ${ex.model_interpretation || nl.overall || "—"}</p>`;
    document.getElementById("histExplain").textContent = ex.historical_explanation || nl.overall || "—";
    document.getElementById("fcExplain").textContent = ex.forecast_explanation || "—";

    renderLocalExplain(data.local_explanation, ex);
    renderAccuracy(data.accuracy, k);

    renderDrivers("posDrivers", ex.positive_contributors, "pos");
    renderDrivers("negDrivers", ex.negative_contributors, "neg");

    clearTimeout(chartTimer);
    chartTimer = setTimeout(() => {
      plotTimeseries(data.charts?.timeseries || {});
      plotLocalContrib(data.charts?.waterfall || data.local_explanation || {});
    }, 40);

    // Render secondary charts (waterfall, partial dependence, pos/neg, feature importance)
    const renderSecondaryCharts = () => {
      plotWaterfall(data.charts?.waterfall || {});
      plotDependence(data.charts?.dependence || {});
      plotPosNeg(ex.positive_contributors, ex.negative_contributors);
      plotImportance(data.factor_impact?.global_importance || []);
    };
    clearTimeout(secondaryChartTimer);
    secondaryChartTimer = setTimeout(renderSecondaryCharts, 90);

    const depSel = document.getElementById("depFeature");
    const feats = (data.available_features || []).map((f) => f.name);
    if (depSel) {
      if (!depSel.options.length && feats.length) {
        fillSelect("depFeature", feats.map((f) => ({ v: f, l: data.available_features.find((x) => x.name === f)?.label || f })), "v", "l", data.charts?.dependence?.feature || feats[0]);
        depSel.addEventListener("change", () => scheduleLoad(false));
      } else if (data.charts?.dependence?.feature) {
        depSel.value = data.charts.dependence.feature;
      }
    }

    const mx = data.models || {};
    document.getElementById("modelXai").innerHTML = `
      <p><strong>Explanation model:</strong> ${mx.explanation_model || "—"}</p>
      <p><strong>Best by RMSE:</strong> ${mx.best_by_rmse || "—"}</p>
      <p><strong>SHAP compatible:</strong> ${(mx.xai_compatible || []).join(", ")}</p>
      <p><strong>Limited:</strong> ${(mx.xai_limited || []).join(", ")}</p>
      <p class="mb-0"><strong>Not supported:</strong> ${(mx.xai_not_supported || []).join(", ")}</p>`;

    // External market drivers
    const extWrap = document.getElementById("externalDriversGrid");
    const extList = document.getElementById("unavailList");
    const extDrivers = data.external_drivers || [];
    if (extWrap) {
      if (extDrivers.length) {
        extWrap.innerHTML = extDrivers.map((d) => `
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
      } else {
        extWrap.innerHTML = "";
      }
    }
    if (extList) {
      if ((data.unavailable_factors || []).length) {
        extList.classList.remove("d-none");
        extList.innerHTML = data.unavailable_factors.map((f) => `<li>${f} — <em>Not available in current dataset.</em></li>`).join("");
      } else {
        extList.classList.add("d-none");
        extList.innerHTML = "";
      }
    }

    const art = data.artifacts || {};
    const img = document.getElementById("imgSummary");
    if (art.shap_summary) {
      img.src = `${art.shap_summary}?t=${Date.now()}`;
      img.style.display = "block";
    } else img.style.display = "none";

    const lime = document.getElementById("limeWrap");
    if (data.lime?.available && data.lime.url) {
      lime.innerHTML = `<button type="button" class="btn btn-ghost btn-sm" id="limeOpen">Load LIME explanation</button>`;
      document.getElementById("limeOpen")?.addEventListener("click", () => {
        lime.innerHTML = `<iframe loading="lazy" src="${data.lime.url}" title="LIME" style="width:100%;height:420px;border:0;border-radius:10px;background:#fff"></iframe>`;
      }, { once: true });
    } else {
      lime.innerHTML = `<span class="xai-unavail">LIME is optional and not required for SHAP factor explanations.</span>`;
    }

    if (!filtersReady && data.filter_options) {
      fillSelect("xaiState", data.filter_options.regions, "code", "name", data.filters?.state);
      fillSelect("xaiYear", data.filter_options.years, null, null, data.filters?.year);
      fillSelect("xaiVehicle", data.filter_options.vehicle_types, null, null, data.filters?.vehicle_type);
      filtersReady = true;
    } else if (data.filters) {
      const st = document.getElementById("xaiState");
      const yr = document.getElementById("xaiYear");
      const vt = document.getElementById("xaiVehicle");
      if (st && data.filters.state) st.value = data.filters.state;
      if (yr && data.filters.year) yr.value = String(data.filters.year);
      if (vt && data.filters.vehicle_type) vt.value = data.filters.vehicle_type;
    }
  }

  async function load(refresh = false) {
    setLoading(true);
    const seq = ++loadSeq;
    if (activeRequest) activeRequest.abort();
    activeRequest = new AbortController();
    const panel = document.getElementById("growthDirPanel");
    if (panel) panel.innerHTML = "<p class='mb-0 text-muted-2'>Loading state-specific explanation…</p>";
    try {
      const depVal = document.getElementById("depFeature")?.value;
      const params = {
        state: document.getElementById("xaiState").value || filters.state,
        year: document.getElementById("xaiYear").value || filters.year,
        vehicle_type: document.getElementById("xaiVehicle").value || filters.vehicle_type,
      };
      if (depVal) params.dep_feature = depVal;
      if (refresh) params.refresh = "1";
      filters = { ...params };
      const cacheKey = JSON.stringify(params);
      if (!refresh && responseCache.has(cacheKey)) {
        applyData(responseCache.get(cacheKey));
        return;
      }
      const data = refresh
        ? await EVForecast.API.xaiRefresh(params, { signal: activeRequest.signal })
        : await EVForecast.API.xaiDashboard(params, { signal: activeRequest.signal });
      if (seq !== loadSeq) return;
      if (!refresh) {
        responseCache.set(cacheKey, data);
        if (responseCache.size > 12) responseCache.delete(responseCache.keys().next().value);
      }
      applyData(data);
      if (refresh) toast("XAI refreshed.", true);
    } catch (e) {
      if (seq !== loadSeq) return;
      if (e.name === "AbortError") return;
      console.error(e);
      toast(e.message || "Failed to load XAI dashboard.", false);
      if (panel) {
        panel.innerHTML = `<p class="mb-2 text-warning">XAI explanation could not be loaded.</p><p class="small text-muted-2 mb-2">${e.message || "The server did not return a response."}</p><button type="button" class="btn btn-ghost btn-sm" id="xaiRetry">Retry</button>`;
        document.getElementById("xaiRetry")?.addEventListener("click", () => load(false), { once: true });
      }
    } finally {
      if (seq === loadSeq) setLoading(false);
    }
  }

  function scheduleLoad(refresh = false) {
    clearTimeout(loadTimer);
    clearTimeout(chartTimer);
    clearTimeout(secondaryChartTimer);
    clearTimeout(localChartTimer);
    loadTimer = setTimeout(() => load(refresh), refresh ? 0 : 250);
  }

  document.getElementById("xaiRefresh").addEventListener("click", () => scheduleLoad(true));
  document.getElementById("xaiReset").addEventListener("click", () => {
    filters = { state: "ALL", year: "", vehicle_type: "All" };
    const state = document.getElementById("xaiState");
    const year = document.getElementById("xaiYear");
    const vehicle = document.getElementById("xaiVehicle");
    if (state) state.value = "ALL";
    if (year && year.options.length) year.value = year.options[year.options.length - 1].value;
    if (vehicle) vehicle.value = "All";
    scheduleLoad(false);
  });
  ["xaiState", "xaiYear", "xaiVehicle"].forEach((id) => {
    document.getElementById(id).addEventListener("change", () => scheduleLoad(false));
  });

  scheduleLoad(false);
})();
