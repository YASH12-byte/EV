(() => {
  "use strict";

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let booted = false;

  function initCharts() {
    if (booted || typeof Chart === "undefined") return;
    booted = true;

    const grid = { color: "rgba(255,255,255,0.05)" };
    const ticks = { color: "rgba(255,255,255,0.35)", font: { size: 9 } };

    const sparkData = Array.from({ length: 16 }, (_, i) => 40 + Math.sin(i / 2) * 12 + i * 2 + Math.random() * 4);
    const salesEl = document.getElementById("chartSales");
    if (salesEl) {
      new Chart(salesEl, {
        type: "line",
        data: {
          labels: sparkData.map((_, i) => i),
          datasets: [{
            data: sparkData,
            borderColor: "#06B6D4",
            backgroundColor: "rgba(37,99,235,0.15)",
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            borderWidth: 2,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: { x: { display: false }, y: { display: false } },
          animation: { duration: 1800 },
        },
      });
    }

    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"];
    const hist = [62, 68, 71, 79, 86, 94, 102, 118];
    const forecast = [null, null, null, null, null, null, 118, 132, 145, 158];
    const fcEl = document.getElementById("chartForecast");
    if (fcEl) {
      new Chart(fcEl, {
        type: "line",
        data: {
          labels: [...months, "Sep", "Oct"],
          datasets: [
            {
              label: "History",
              data: [...hist, null, null],
              borderColor: "#2563EB",
              backgroundColor: "rgba(37,99,235,0.12)",
              fill: true,
              tension: 0.35,
              pointRadius: 0,
              borderWidth: 2,
            },
            {
              label: "Forecast",
              data: forecast,
              borderColor: "#10B981",
              borderDash: [5, 4],
              tension: 0.35,
              pointRadius: 2,
              pointBackgroundColor: "#10B981",
              borderWidth: 2,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks, grid: { display: false } },
            y: { ticks, grid },
          },
          animation: { duration: 2000 },
        },
      });
    }

    const ts = Array.from({ length: 40 }, (_, i) =>
      50 + Math.sin(i / 3) * 18 + Math.cos(i / 5) * 10 + (i % 7 === 0 ? 8 : 0)
    );
    const tsEl = document.getElementById("chartTS");
    if (tsEl) {
      new Chart(tsEl, {
        type: "line",
        data: {
          labels: ts.map((_, i) => i),
          datasets: [{
            data: ts,
            borderColor: "#06B6D4",
            backgroundColor: "rgba(6,182,212,0.1)",
            fill: true,
            tension: 0.25,
            pointRadius: 0,
            borderWidth: 1.5,
          }],
        },
        options: {
          responsive: true,
          plugins: { legend: { display: false } },
          scales: {
            x: { display: false },
            y: { ticks, grid },
          },
          animation: false,
        },
      });

      const tsChart = Chart.getChart("chartTS");
      if (tsChart && !reduced) {
        setInterval(() => {
          const d = tsChart.data.datasets[0].data;
          d.shift();
          d.push(50 + Math.sin(Date.now() / 400) * 18 + Math.cos(Date.now() / 700) * 10 + Math.random() * 4);
          tsChart.update("none");
        }, 900);
      }
    }

    requestAnimationFrame(() => {
      const conf = document.getElementById("meterConf");
      const batt = document.getElementById("meterBatt");
      if (conf) conf.style.width = "96%";
      if (batt) batt.style.width = "91%";
    });
  }

  function animateLiveStats() {
    if (reduced) return;
    const demand = document.getElementById("liveDemand");
    const stations = document.getElementById("liveStations");
    const rmse = document.getElementById("liveRmse");
    const sales = document.getElementById("kpiSales");
    const conf = document.getElementById("kpiConf");

    setInterval(() => {
      if (demand) demand.textContent = `+${(10 + Math.random() * 6).toFixed(0)}%`;
      if (stations) stations.textContent = String(1260 + Math.floor(Math.random() * 40)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
      if (rmse) rmse.textContent = (0.035 + Math.random() * 0.015).toFixed(3);
      if (sales) sales.textContent = `+${(22 + Math.random() * 5).toFixed(1)}%`;
      if (conf) conf.textContent = `${(95.5 + Math.random() * 1.8).toFixed(1)}%`;
    }, 2800);
  }

  window.EVLiveAnalytics = {
    init() {
      initCharts();
      animateLiveStats();
    },
  };
})();
