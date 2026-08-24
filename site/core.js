/**
 * GitHub Pages adapter (static hosting cannot run Flask).
 * Provides demo login, CSV charts, and correct /EV/ links.
 */
(function () {
  "use strict";

  function repoBase() {
    if (!location.hostname.endsWith("github.io")) {
      const path = location.pathname;
      if (path.endsWith(".html") || path.endsWith("/")) {
        const dir = path.replace(/[^/]+$/, "");
        return dir || "/";
      }
      return "/";
    }
    const parts = location.pathname.split("/").filter(Boolean);
    return parts.length ? "/" + parts[0] + "/" : "/";
  }

  const BASE = repoBase();
  const FILE = {
    "/": "index.html",
    "/login": "index.html",
    "/register": "register.html",
    "/home": "home.html",
    "/dashboard": "dashboard.html",
    "/admin": "dashboard.html",
    "/prediction": "prediction.html",
    "/dataset": "dataset.html",
    "/about": "about.html",
    "/comparison": "comparison.html",
    "/contact": "contact.html",
    "/xai": "about.html",
  };

  window.EVPages = {
    base: BASE,
    href(path) {
      const key = String(path || "/").split("#")[0].split("?")[0];
      return BASE + (FILE[key] || "index.html");
    },
    asset(path) {
      return BASE + path.replace(/^\//, "");
    },
  };

  const TOKEN_KEY = "evforecast_token";
  const USER_KEY = "evforecast_user";

  function saveSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function currentUser() {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || "null");
    } catch {
      return null;
    }
  }

  function login({ email, password }) {
    email = String(email || "").trim().toLowerCase();
    password = String(password || "");
    if (email === "admin@evforecast.edu" && password === "Admin@123") {
      return {
        token: "github-pages-demo",
        user: { name: "Project Admin", email, role: "admin" },
      };
    }
    const users = JSON.parse(localStorage.getItem("evforecast_pages_users") || "[]");
    const found = users.find((u) => u.email === email && u.password === password);
    if (found) {
      return {
        token: "github-pages-demo",
        user: { name: found.name || "User", email, role: "user" },
      };
    }
    const err = new Error("Invalid email or password");
    err.data = { message: "Invalid email or password. Demo: admin@evforecast.edu / Admin@123" };
    throw err;
  }

  window.EVForecast = window.EVForecast || {};
  window.EVForecast.saveSession = saveSession;
  window.EVForecast.clearSession = clearSession;
  window.EVForecast.currentUser = currentUser;
  window.EVForecast.API = window.EVForecast.API || {};
  window.EVForecast.API.login = (body) => Promise.resolve().then(() => login(body));

  window.EVForecast.API.register = (body) =>
    Promise.resolve().then(() => {
      const email = String(body.email || "").trim().toLowerCase();
      const password = String(body.password || "");
      const name = String(body.name || "User");
      if (!email || password.length < 6) {
        const err = new Error("Use a valid email and password (6+ characters).");
        err.data = { message: err.message };
        throw err;
      }
      const users = JSON.parse(localStorage.getItem("evforecast_pages_users") || "[]");
      if (users.some((u) => u.email === email)) {
        const err = new Error("Account already exists. Please login.");
        err.data = { message: err.message };
        throw err;
      }
      users.push({ email, password, name });
      localStorage.setItem("evforecast_pages_users", JSON.stringify(users));
      return { ok: true };
    });

  async function fetchText(rel) {
    const res = await fetch(window.EVPages.asset(rel));
    if (!res.ok) throw new Error("Could not load " + rel);
    return res.text();
  }

  function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    const headers = lines[0].split(",").map((h) => h.trim());
    return lines.slice(1).filter(Boolean).map((line) => {
      const cols = line.split(",");
      const row = {};
      headers.forEach((h, i) => {
        row[h] = cols[i];
      });
      return row;
    });
  }

  window.EVPagesData = {
    async national() {
      const rows = parseCSV(await fetchText("data/processed/ev_registrations_national_annual.csv"));
      return rows
        .filter((r) => r.State === "ALL" && (r.VehicleType === "All" || !r.VehicleType))
        .map((r) => ({ year: Number(r.Year), value: Number(r.Registrations) }))
        .filter((r) => Number.isFinite(r.year) && Number.isFinite(r.value))
        .sort((a, b) => a.year - b.year);
    },
    async annual() {
      return parseCSV(await fetchText("data/processed/ev_registrations_annual.csv")).map((r) => ({
        state: r.State,
        vehicle: r.VehicleType,
        year: Number(r.Year),
        value: Number(r.Registrations),
      }));
    },
    async comparison() {
      const res = await fetch(window.EVPages.asset("models/saved/comparison_results.json"));
      return res.json();
    },
    forecast(series, horizon) {
      const pts = series.filter((p) => Number.isFinite(p.value) && p.value > 0);
      if (pts.length < 2) return [];
      const last = pts.slice(-4);
      const growths = [];
      for (let i = 1; i < last.length; i++) {
        if (last[i - 1].value > 0) growths.push(last[i].value / last[i - 1].value);
      }
      const g = growths.length ? growths.reduce((a, b) => a + b, 0) / growths.length : 1.08;
      const rate = Math.min(1.35, Math.max(0.85, g));
      const out = [];
      let y = pts[pts.length - 1].year;
      let v = pts[pts.length - 1].value;
      for (let i = 0; i < horizon; i++) {
        y += 1;
        v = Math.round(v * rate);
        out.push({ year: y, value: v });
      }
      return out;
    },
  };

  window.EVPages.requireAuth = function () {
    if (!currentUser()) location.replace(window.EVPages.href("/login"));
  };

  window.EVPages.bindLogout = function () {
    const el = document.getElementById("navAuth");
    const user = currentUser();
    if (!el) return;
    if (user) {
      el.innerHTML =
        '<button class="btn btn-glow" id="logoutBtn" type="button">Logout · ' +
        user.name.split(" ")[0] +
        "</button>";
      document.getElementById("logoutBtn")?.addEventListener("click", () => {
        clearSession();
        location.href = window.EVPages.href("/login");
      });
    } else {
      el.innerHTML = '<a class="btn btn-glow" href="' + window.EVPages.href("/login") + '">Login</a>';
    }
  };

  // Keep Bootstrap nav auth links on the /EV/ site (override Flask absolute paths).
  if (typeof window.updateNavAuth === "function") {
    window.updateNavAuth = window.EVPages.bindLogout;
  }
  document.addEventListener("DOMContentLoaded", () => window.EVPages.bindLogout());
})();
