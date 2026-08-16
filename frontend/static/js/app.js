const TOKEN_KEY = "evforecast_token";
const USER_KEY = "evforecast_user";

const API = {
  async request(path, options = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers.Authorization = `Bearer ${token}`;
    let res;
    try {
      res = await fetch(path, { ...options, headers });
    } catch (netErr) {
      const err = new Error(
        "Cannot reach Flask at this URL. Start the app with: python run.py (http://127.0.0.1:5000)"
      );
      err.status = 0;
      err.data = {};
      throw err;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(
        data.message || `Request failed (${res.status} ${path})`
      );
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  },
  login: (body) => API.request("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  register: (body) => API.request("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  me: () => API.request("/api/auth/me"),
  contact: (body) => API.request("/api/contact", { method: "POST", body: JSON.stringify(body) }),
  summary: () => API.request("/api/dataset/summary"),
  timeseries: (region) => API.request(`/api/dataset/timeseries${region ? `?region=${encodeURIComponent(region)}` : ""}`),
  comparison: () => API.request("/api/models/comparison"),
  importance: () => API.request("/api/models/feature-importance"),
  regions: () => API.request("/api/regions"),
  snapshot: (region = "ALL") =>
    API.request(`/api/dashboard/snapshot?region=${encodeURIComponent(region)}`),
  predict: (body) => API.request("/api/predict", { method: "POST", body: JSON.stringify(body) }),
  forecast: (region, months = 6, target = "registrations", vehicleType = "All") =>
    API.request(
      `/api/forecast?region=${encodeURIComponent(region)}&months=${months}` +
        `&target=${encodeURIComponent(target)}&vehicle_type=${encodeURIComponent(vehicleType)}`
    ),
  xai: () => API.request("/api/xai/insights"),
  adminStats: () => API.request("/api/admin/stats"),
  adminUsers: () => API.request("/api/admin/users"),
  adminPredictions: () => API.request("/api/admin/predictions"),
  adminContacts: () => API.request("/api/admin/contacts"),
  adminContactStatus: (id, status) =>
    API.request(`/api/admin/contacts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
};

function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function currentUser() {
  try { return JSON.parse(localStorage.getItem(USER_KEY) || "null"); } catch { return null; }
}

function updateNavAuth() {
  const el = document.getElementById("navAuth");
  if (!el) return;
  const user = currentUser();
  if (user) {
    el.innerHTML = `
      <div class="dropdown">
        <button class="btn btn-glow dropdown-toggle" data-bs-toggle="dropdown">${user.name.split(" ")[0]}</button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li><a class="dropdown-item" href="/dashboard">Dashboard</a></li>
          ${user.role === "admin" ? '<li><a class="dropdown-item" href="/admin">Admin</a></li>' : ""}
          <li><hr class="dropdown-divider" /></li>
          <li><button class="dropdown-item" id="logoutBtn">Logout</button></li>
        </ul>
      </div>`;
    const btn = document.getElementById("logoutBtn");
    if (btn) btn.addEventListener("click", () => { clearSession(); location.href = "/login"; });
  } else {
    el.innerHTML = `<a class="btn btn-glow" href="/login">Login</a>`;
  }
}

function spawnParticles(rootSelector, count = 18) {
  const root = document.querySelector(rootSelector);
  if (!root) return;
  const wrap = document.createElement("div");
  wrap.className = "floating-particles";
  wrap.style.cssText = "position:absolute;inset:0;overflow:hidden;pointer-events:none;";
  for (let i = 0; i < count; i++) {
    const s = document.createElement("span");
    s.style.left = `${Math.random() * 100}%`;
    s.style.animationDelay = `${Math.random() * 8}s`;
    s.style.animationDuration = `${7 + Math.random() * 6}s`;
    s.style.opacity = `${0.35 + Math.random() * 0.5}`;
    wrap.appendChild(s);
  }
  root.appendChild(wrap);
}

function spawnBackgroundParticles(count = 28) {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const root = document.getElementById("bgParticles");
  if (!root || root.childElementCount) return;
  for (let i = 0; i < count; i++) {
    const s = document.createElement("span");
    if (i % 5 === 0) s.className = "streak";
    const drift = `${Math.round((Math.random() - 0.5) * 120)}px`;
    s.style.left = `${Math.random() * 100}%`;
    s.style.setProperty("--drift", drift);
    s.style.animationDelay = `${Math.random() * 14}s`;
    s.style.animationDuration = `${10 + Math.random() * 14}s`;
    s.style.opacity = `${0.25 + Math.random() * 0.55}`;
    root.appendChild(s);
  }
}

function enableBackground3DParallax() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  if (window.matchMedia("(pointer: coarse)").matches) return;
  const root = document.documentElement;
  let raf = 0;
  let targetX = 0;
  let targetY = 0;
  let curX = 0;
  let curY = 0;

  const tick = () => {
    curX += (targetX - curX) * 0.08;
    curY += (targetY - curY) * 0.08;
    root.style.setProperty("--tilt-x", `${curX.toFixed(3)}deg`);
    root.style.setProperty("--tilt-y", `${curY.toFixed(3)}deg`);
    raf = requestAnimationFrame(tick);
  };

  window.addEventListener("pointermove", (e) => {
    const nx = (e.clientX / window.innerWidth) * 2 - 1;
    const ny = (e.clientY / window.innerHeight) * 2 - 1;
    targetY = nx * 6;
    targetX = ny * -4;
  }, { passive: true });

  raf = requestAnimationFrame(tick);
  window.addEventListener("pagehide", () => cancelAnimationFrame(raf), { once: true });
}

function enableCard3DTilt(selector = ".login-from-bag") {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const card = document.querySelector(selector);
  if (!card) return;
  card.classList.add("is-tilting");
  const max = 10;
  card.addEventListener("pointermove", (e) => {
    const r = card.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width;
    const py = (e.clientY - r.top) / r.height;
    const rotY = (px - 0.5) * max * 2;
    const rotX = (0.5 - py) * max * 2;
    card.style.transform = `perspective(1000px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(12px)`;
  });
  card.addEventListener("pointerleave", () => {
    card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0)";
  });
}

document.addEventListener("DOMContentLoaded", () => {
  updateNavAuth();
  spawnBackgroundParticles();
  enableBackground3DParallax();
});

window.EVForecast = { API, saveSession, clearSession, currentUser, spawnParticles, enableCard3DTilt };
