(() => {
  const fmt = (n) =>
    n == null || !Number.isFinite(Number(n)) ? "—" : Math.round(Number(n)).toLocaleString("en-IN");
  const fmtPct = (n) =>
    n == null || !Number.isFinite(Number(n)) ? "—" : `${Number(n).toFixed(1)}%`;

  let annual = [];
  let importance = { ranking: [] };
  let nationalPack = null;
  let tsChart;
  let localChart;
  let impChart;

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
      codes.map((c) => `<option value="${c}">${c} · ${stateName(c)}</option>`).join("");
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

  function fromNationalPack() {
    const k = nationalPack.kpis || {};
    const ch = nationalPack.charts?.timeseries || {};
    const loc = nationalPack.local_explanation || {};
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
    const nl = loc.natural_language || {};
    document.getElementById("predCard").innerHTML =
      `<p>${nl.overall || nationalPack.explanation_panel?.main_reason || ""}</p>` +
      `<p class="mb-0">${nl.causality_note || nationalPack.disclaimer || ""}</p>`;
    document.getElementById("localExplainSummary").textContent = nl.summary || "";
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
    const dir = expl.growth_pct >= 0 ? "increase" : "decrease";
    document.getElementById("predCard").innerHTML =
      `<p>For <strong>${state === "ALL" ? "All India" : state}</strong> in ${expl.year}, registrations ${dir} ` +
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

  function refresh() {
    const state = document.getElementById("xaiState").value;
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
    annual = await EVPagesData.annual();
    importance = await EVPagesData.shapImportance();
    try {
      nationalPack = await EVPagesData.nationalXai();
    } catch (_) {
      nationalPack = null;
    }
    fillStates();
    fillYears(EVPagesData.seriesFor(annual, "ALL", "All"));
    drawImp();
    refresh();
  })();
})();
