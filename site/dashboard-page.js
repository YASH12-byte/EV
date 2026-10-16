/**
 * Dashboard for static hosts: uses Flask /api/dashboard/snapshot when available.
 */
(function () {
  "use strict";

  const fmt = (n) => (!Number.isFinite(Number(n)) ? "—" : Math.round(Number(n)).toLocaleString("en-IN"));

  function lineChart(id, labels, data, color) {
    return new Chart(document.getElementById(id), {
      type: "line",
      data: {
        labels,
        datasets: [{
          data,
          borderColor: color,
          backgroundColor: color.replace(")", ",0.15)").replace("rgb", "rgba"),
          fill: true,
          tension: 0.35,
          pointRadius: 0,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8fa3b0", maxTicksLimit: 10 }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
        },
      },
    });
  }

  function yearlySum(rows, state) {
    const by = {};
    rows.forEach((r) => {
      if (state !== "ALL" && r.state !== state) return;
      if (!Number.isFinite(r.value) || !Number.isFinite(r.year)) return;
      by[r.year] = (by[r.year] || 0) + r.value;
    });
    const years = Object.keys(by).map(Number).sort((a, b) => a - b);
    return { years, values: years.map((y) => by[y]) };
  }

  let charts = [];

  function destroyCharts() {
    charts.forEach((c) => c.destroy());
    charts = [];
  }

  async function paintFromApi(region) {
    const snap = await EVForecast.API.snapshot(region);
    if (!snap.ok) throw new Error(snap.message || "Snapshot failed");

    const sel = document.getElementById("regionSelect");
    const regions = snap.regions || [];
    if (regions.length && sel.options.length <= 1) {
      sel.innerHTML = regions
        .map((r) => {
          const code = r.code || r;
          const name = r.name || (typeof evStateName === "function" ? evStateName(code) : code);
          return `<option value="${code}">${name}</option>`;
        })
        .join("");
      sel.value = snap.region?.code || region || "ALL";
    }

    const k = snap.kpis || {};
    document.getElementById("kpiRegs").textContent = fmt(k.total_registrations);
    document.getElementById("kpiTx").textContent = fmt(k.total_transactions);
    document.getElementById("kpiRev").textContent = fmt(k.total_revenue);

    const title = document.getElementById("regChartTitle");
    if (title) {
      title.textContent = `${snap.region?.name || "All India"} — registration trend + forecast (saved models)`;
    }

    const histDates = snap.forecast?.history?.dates || snap.registration_trend?.dates || [];
    const histVals = snap.forecast?.history?.ev_sales || snap.registration_trend?.values || [];
    const futDates = snap.forecast?.forecast?.dates || [];
    const futVals = snap.forecast?.forecast?.ev_sales || [];
    const regLabels = [...histDates, ...futDates];
    const regData = [...histVals, ...futVals];

    destroyCharts();
    charts.push(lineChart("regChart", regLabels, regData, "rgb(45,212,191)"));

    const txDates = snap.transaction_trend?.dates || [];
    const txVals = snap.transaction_trend?.values || [];
    charts.push(lineChart("txChart", txDates, txVals, "rgb(56,189,248)"));

    const revDates = snap.revenue_trend?.dates || [];
    const revVals = snap.revenue_trend?.values || [];
    charts.push(lineChart("revChart", revDates, revVals, "rgb(245,185,66)"));

    const rank = (snap.xai?.ranking || []).slice(0, 6);
    charts.push(
      new Chart(document.getElementById("impChart"), {
        type: "bar",
        data: {
          labels: rank.map((r) => r.label || r.feature),
          datasets: [{ data: rank.map((r) => r.importance), backgroundColor: "rgba(45,212,191,0.45)", borderColor: "#2dd4bf" }],
        },
        options: {
          indexAxis: "y",
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
            y: { ticks: { color: "#cfe3ec" }, grid: { display: false } },
          },
        },
      })
    );
  }

  async function paintFromStatic(state) {
    const annual = await EVPagesData.annual();
    const tx = await EVPagesData.monthly("data/processed/ev_transactions_monthly.csv", "EV_Transactions");
    const rev = await EVPagesData.monthly("data/processed/ev_revenue_monthly.csv", "Revenue");
    const shap = await EVPagesData.shapImportance();

    const sel = document.getElementById("regionSelect");
    if (!sel.options.length) {
      const states = ["ALL", ...[...new Set(annual.map((r) => r.state))].filter(Boolean).sort()];
      sel.innerHTML = states
        .map((s) => `<option value="${s}">${typeof evStateName === "function" ? evStateName(s) : s === "ALL" ? "All India" : s}</option>`)
        .join("");
    }

    const title = document.getElementById("regChartTitle");
    if (title) {
      title.textContent = `${typeof evStateName === "function" ? evStateName(state) : state} — registration trend + forecast`;
    }

    const regs = yearlySum(annual, state);
    const txs = yearlySum(tx, state);
    const revs = yearlySum(rev, state);
    const hist = regs.years.map((y, i) => ({ year: y, value: regs.values[i] }));
    const fut = EVPagesData.forecast(hist, 3);

    document.getElementById("kpiRegs").textContent = fmt(regs.values.reduce((a, b) => a + b, 0));
    document.getElementById("kpiTx").textContent = fmt(txs.values.reduce((a, b) => a + b, 0));
    document.getElementById("kpiRev").textContent = fmt(revs.values.reduce((a, b) => a + b, 0));

    destroyCharts();
    charts.push(lineChart("regChart", [...regs.years, ...fut.map((p) => p.year)], [...regs.values, ...fut.map((p) => p.value)], "rgb(45,212,191)"));
    charts.push(lineChart("txChart", txs.years, txs.values, "rgb(56,189,248)"));
    charts.push(lineChart("revChart", revs.years, revs.values, "rgb(245,185,66)"));

    const rank = (shap.ranking || []).slice(0, 6);
    charts.push(
      new Chart(document.getElementById("impChart"), {
        type: "bar",
        data: {
          labels: rank.map((r) => r.feature),
          datasets: [{ data: rank.map((r) => r.importance), backgroundColor: "rgba(45,212,191,0.45)", borderColor: "#2dd4bf" }],
        },
        options: {
          indexAxis: "y",
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: "#8fa3b0" }, grid: { color: "rgba(255,255,255,0.04)" } },
            y: { ticks: { color: "#cfe3ec" }, grid: { display: false } },
          },
        },
      })
    );
  }

  async function paint() {
    const region = document.getElementById("regionSelect").value || "ALL";
    try {
      if (window.EVPages?.hasBackend) {
        await paintFromApi(region);
      } else {
        await paintFromStatic(region);
      }
    } catch (err) {
      console.warn("Dashboard API failed, using static data:", err);
      await paintFromStatic(region);
    }
  }

  window.EVStaticPages = window.EVStaticPages || {};
  window.EVStaticPages.initDashboard = async function () {
    await window.EVPages.ready;
    const sel = document.getElementById("regionSelect");
    sel.addEventListener("change", paint);
    await paint();
  };
})();
