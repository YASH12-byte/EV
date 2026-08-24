(() => {
  const fmt = (n) => (n == null || Number.isNaN(Number(n)) ? "—" : Math.round(Number(n)).toLocaleString("en-IN"));
  const fmtPct = (n) => (n == null || !Number.isFinite(Number(n)) ? "—" : `${Number(n).toFixed(1)}%`);
  let impChart = null;
  let filters = { state: "ALL", year: "", vehicle_type: "All" };
  let loadTimer = null;
  let loadSeq = 0;

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
    plotLocalContrib(local.waterfall || { base: local.baseline, contributions: contribs, final: local.prediction });
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
    document.getElementById("kpiCurrent").textContent = fmt(k.current_sales);
    document.getElementById("kpiPred").textContent = fmt(k.predicted_sales);
    document.getElementById("kpiGrowth").textContent = fmtPct(k.growth_pct);
    document.getElementById("kpiAcc").textContent = k.explanation_model_accuracy_approx != null
      ? `${k.explanation_model_accuracy_approx}% (RF, 100 − MAPE)` : (k.forecast_accuracy_approx != null
      ? `${k.forecast_accuracy_approx}% (best model)` : "—");
    document.getElementById("kpiPos").textContent = k.top_positive_factor || "—";
    document.getElementById("kpiNeg").textContent = k.top_negative_factor || "—";

    const pc = data.prediction_card || {};
    document.getElementById("predCard").innerHTML = `
      <p><strong>Predicted EV Sales:</strong> ${fmt(pc.predicted_ev_sales)}</p>
      <p><strong>Previous Period:</strong> ${fmt(pc.previous_period_sales)}</p>
      <p><strong>Expected Growth:</strong> ${fmtPct(pc.expected_growth_pct)}</p>
      <p><strong>Direction:</strong> ${pc.direction || "—"} · <strong>Trend:</strong> ${pc.overall_trend || "—"}</p>
      <p><strong>Main + factor:</strong> ${pc.main_positive_factor || "—"}</p>
      <p><strong>Main − factor:</strong> ${pc.main_negative_factor || "—"}</p>
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

    plotTimeseries(data.charts?.timeseries || {});

    // Defer secondary charts so KPIs and local explanation render first
    requestAnimationFrame(() => {
      plotWaterfall(data.charts?.waterfall || {});
      plotDependence(data.charts?.dependence || {});
      plotPosNeg(ex.positive_contributors, ex.negative_contributors);
      plotImportance(data.factor_impact?.global_importance || []);
    });

    const depSel = document.getElementById("depFeature");
    const feats = (data.available_features || []).map((f) => f.name);
    if (!depSel.options.length && feats.length) {
      fillSelect("depFeature", feats.map((f) => ({ v: f, l: data.available_features.find((x) => x.name === f)?.label || f })), "v", "l");
      depSel.addEventListener("change", () => load(false));
    }

    const mx = data.models || {};
    document.getElementById("modelXai").innerHTML = `
      <p><strong>Explanation model:</strong> ${mx.explanation_model || "—"}</p>
      <p><strong>Best by RMSE:</strong> ${mx.best_by_rmse || "—"}</p>
      <p><strong>SHAP compatible:</strong> ${(mx.xai_compatible || []).join(", ")}</p>
      <p><strong>Limited:</strong> ${(mx.xai_limited || []).join(", ")}</p>
      <p class="mb-0"><strong>Not supported:</strong> ${(mx.xai_not_supported || []).join(", ")}</p>`;

    document.getElementById("unavailList").innerHTML = (data.unavailable_factors || [])
      .map((f) => `<li>${f} — <em>Not available in current dataset.</em></li>`).join("");

    const art = data.artifacts || {};
    const img = document.getElementById("imgSummary");
    if (art.shap_summary) {
      img.src = `${art.shap_summary}?t=${Date.now()}`;
      img.style.display = "block";
    } else img.style.display = "none";

    const lime = document.getElementById("limeWrap");
    if (data.lime?.available && data.lime.url) {
      lime.innerHTML = `<iframe loading="lazy" src="${data.lime.url}" title="LIME" style="width:100%;height:420px;border:0;border-radius:10px;background:#fff"></iframe>`;
    } else {
      lime.innerHTML = `<span class="xai-unavail">LIME not generated. Run: python src/xai_lime.py</span>`;
    }

    if (data.filter_options) {
      fillSelect("xaiState", data.filter_options.regions, "code", "name", data.filters?.state);
      fillSelect("xaiYear", data.filter_options.years, null, null, data.filters?.year);
      fillSelect("xaiVehicle", data.filter_options.vehicle_types, null, null, data.filters?.vehicle_type);
    }
  }

  async function load(refresh = false) {
    setLoading(true);
    const seq = ++loadSeq;
    try {
      const params = {
        state: document.getElementById("xaiState").value || filters.state,
        year: document.getElementById("xaiYear").value || filters.year,
        vehicle_type: document.getElementById("xaiVehicle").value || filters.vehicle_type,
      };
      if (refresh) params.refresh = "1";
      filters = { ...params };
      const data = refresh
        ? await EVForecast.API.xaiRefresh(params)
        : await EVForecast.API.xaiDashboard(params);
      if (seq !== loadSeq) return;
      applyData(data);
      if (refresh) toast("XAI refreshed.", true);
    } catch (e) {
      if (seq !== loadSeq) return;
      console.error(e);
      toast(e.message || "Failed to load XAI dashboard.", false);
    } finally {
      if (seq === loadSeq) setLoading(false);
    }
  }

  function scheduleLoad(refresh = false) {
    clearTimeout(loadTimer);
    loadTimer = setTimeout(() => load(refresh), refresh ? 0 : 250);
  }

  document.getElementById("xaiRefresh").addEventListener("click", () => scheduleLoad(true));
  document.getElementById("xaiReset").addEventListener("click", () => {
    filters = { state: "ALL", year: "", vehicle_type: "All" };
    scheduleLoad(false);
  });
  ["xaiState", "xaiYear", "xaiVehicle"].forEach((id) => {
    document.getElementById(id).addEventListener("change", () => scheduleLoad(false));
  });

  scheduleLoad(false);
})();
