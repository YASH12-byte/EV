(() => {
  "use strict";

  if (window.EVForecast?.currentUser?.()) {
    location.replace("/home");
    return;
  }

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const els = {
    root: document.getElementById("lpRoot"),
    cinema: document.getElementById("lpCinema"),
    stage: document.getElementById("lpStage"),
    carsCanvas: document.getElementById("lpCarsCanvas"),
    gateBurst: document.getElementById("lpGateBurst"),
    sceneLabel: document.getElementById("lpSceneLabel"),
    progress: document.getElementById("lpProgress"),
    cinemaUi: document.getElementById("lpCinemaUi"),
    workspace: document.getElementById("lpWorkspace"),
    card: document.getElementById("lpCard"),
    form: document.getElementById("loginForm"),
    error: document.getElementById("loginError"),
    btn: document.getElementById("lpLoginBtn"),
    togglePass: document.getElementById("lpTogglePass"),
    password: document.getElementById("lpPassword"),
    remember: document.getElementById("lpRemember"),
    forgot: document.getElementById("lpForgot"),
    success: document.getElementById("lpSuccess"),
    canvas: document.getElementById("lpCanvas"),
  };

  let cinemaDone = false;
  let cars3d = null;
  const timers = [];

  function later(fn, ms) {
    const id = setTimeout(fn, ms);
    timers.push(id);
    return id;
  }

  function clearTimers() {
    while (timers.length) clearTimeout(timers.pop());
  }

  function setProgress(pct, label) {
    if (els.progress) els.progress.style.width = `${pct}%`;
    if (label && els.sceneLabel) els.sceneLabel.textContent = label;
  }

  function revealWorkspace() {
    if (cinemaDone) return;
    cinemaDone = true;
    clearTimers();
    cars3d?.setState("done");
    els.cinema?.classList.add("is-done");
    els.cinema?.classList.remove("is-approaching", "is-gate-open");
    els.workspace?.classList.add("is-visible");
    els.workspace?.setAttribute("aria-hidden", "false");
    setTimeout(() => {
      if (window.EVForecast?.enableCard3DTilt) {
        EVForecast.enableCard3DTilt("#lpCard");
      }
      els.form?.querySelector('input[name="email"]')?.focus();
    }, 400);
  }

  /**
   * Sequence (must finish before login opens):
   * 1) 3D EVs approach closed gate
   * 2) Gate opens
   * 3) Burst / portal
   * 4) Login interface appears
   */
  function playCinema() {
    if (reduced) {
      setProgress(100, "Opening secure access…");
      later(revealWorkspace, 250);
      return;
    }

    const cinema = els.cinema;
    if (!cinema) {
      later(revealWorkspace, 200);
      return;
    }

    if (window.EVCars3D && els.carsCanvas) {
      cars3d = EVCars3D.create(els.carsCanvas);
    }

    els.workspace?.classList.remove("is-visible");
    els.workspace?.setAttribute("aria-hidden", "true");
    cinema.classList.remove("is-done", "is-approaching", "is-gate-open");
    setProgress(8, "EV fleet approaching secure gate…");

    // Scene 1 — cars approach
    cars3d?.setState("approach");
    requestAnimationFrame(() => {
      cinema.classList.add("is-approaching");
      setProgress(35, "EV fleet approaching secure gate…");
    });

    // Scene 2 — gate opens
    later(() => {
      cinema.classList.add("is-gate-open");
      cars3d?.setState("open");
      setProgress(72, "Gate unlocking · Access granted…");
    }, 2800);

    // Scene 3 — portal burst
    later(() => {
      els.gateBurst?.classList.add("is-active");
      setProgress(92, "Entering forecasting platform…");
    }, 4200);

    // Scene 4 — reveal login
    later(() => {
      setProgress(100, "Welcome");
      revealWorkspace();
    }, 5600);
  }

  /* ----- Three.js particle field ----- */
  function initThree() {
    if (!els.canvas || typeof THREE === "undefined" || reduced) return;

    const renderer = new THREE.WebGLRenderer({
      canvas: els.canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.z = 28;

    const count = 900;
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const palette = [
      [0.145, 0.388, 0.922],
      [0.024, 0.714, 0.831],
      [0.063, 0.725, 0.506],
    ];

    for (let i = 0; i < count; i++) {
      const i3 = i * 3;
      positions[i3] = (Math.random() - 0.5) * 60;
      positions[i3 + 1] = (Math.random() - 0.5) * 36;
      positions[i3 + 2] = (Math.random() - 0.5) * 40;
      const c = palette[i % 3];
      colors[i3] = c[0];
      colors[i3 + 1] = c[1];
      colors[i3 + 2] = c[2];
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size: 0.12,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });

    const points = new THREE.Points(geo, mat);
    scene.add(points);

    const linkCount = 80;
    const linkPos = new Float32Array(linkCount * 6);
    for (let i = 0; i < linkCount; i++) {
      const a = Math.floor(Math.random() * count) * 3;
      const b = Math.floor(Math.random() * count) * 3;
      linkPos[i * 6] = positions[a];
      linkPos[i * 6 + 1] = positions[a + 1];
      linkPos[i * 6 + 2] = positions[a + 2];
      linkPos[i * 6 + 3] = positions[b];
      linkPos[i * 6 + 4] = positions[b + 1];
      linkPos[i * 6 + 5] = positions[b + 2];
    }
    const linkGeo = new THREE.BufferGeometry();
    linkGeo.setAttribute("position", new THREE.BufferAttribute(linkPos, 3));
    const links = new THREE.LineSegments(
      linkGeo,
      new THREE.LineBasicMaterial({
        color: 0x2563eb,
        transparent: true,
        opacity: 0.12,
      })
    );
    scene.add(links);

    let mouseX = 0;
    let mouseY = 0;
    window.addEventListener("pointermove", (e) => {
      mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY = (e.clientY / window.innerHeight - 0.5) * 2;
    });

    function onResize() {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }
    window.addEventListener("resize", onResize);

    const clock = new THREE.Clock();
    function tick() {
      const t = clock.getElapsedTime();
      points.rotation.y = t * 0.04 + mouseX * 0.15;
      points.rotation.x = Math.sin(t * 0.2) * 0.08 + mouseY * 0.1;
      links.rotation.copy(points.rotation);
      camera.position.x += (mouseX * 2 - camera.position.x) * 0.03;
      camera.position.y += (-mouseY * 1.5 - camera.position.y) * 0.03;
      camera.lookAt(0, 0, 0);
      renderer.render(scene, camera);
      requestAnimationFrame(tick);
    }
    tick();
  }

  /* ----- Auth UI ----- */
  els.togglePass?.addEventListener("click", () => {
    const shown = els.password.type === "text";
    els.password.type = shown ? "password" : "text";
    els.togglePass.classList.toggle("is-shown", !shown);
    els.togglePass.setAttribute("aria-label", shown ? "Show password" : "Hide password");
  });

  els.forgot?.addEventListener("click", (e) => {
    e.preventDefault();
    els.error.textContent = "Password reset is available from your institute admin.";
    els.error.classList.add("show");
  });

  try {
    const remembered = localStorage.getItem("evforecast_remember_email");
    if (remembered && els.form) {
      els.form.email.value = remembered;
      if (els.remember) els.remember.checked = true;
    }
  } catch (_) { /* ignore */ }

  els.btn?.addEventListener("pointerdown", (e) => {
    const ripple = els.btn.querySelector(".lp-btn-ripple");
    if (!ripple) return;
    const rect = els.btn.getBoundingClientRect();
    ripple.style.left = `${e.clientX - rect.left}px`;
    ripple.style.top = `${e.clientY - rect.top}px`;
    els.btn.classList.remove("is-rippling");
    void els.btn.offsetWidth;
    els.btn.classList.add("is-rippling");
  });

  els.form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    els.error.classList.remove("show");
    const fd = new FormData(els.form);
    const email = String(fd.get("email") || "").trim().toLowerCase();
    const password = String(fd.get("password") || "");
    const EMAIL_RE = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

    if (!EMAIL_RE.test(email)) {
      els.error.textContent = "Please enter a valid email address.";
      els.error.classList.add("show");
      return;
    }
    if (!password) {
      els.error.textContent = "Please enter your password.";
      els.error.classList.add("show");
      return;
    }

    els.btn.classList.add("is-loading");
    els.card.classList.add("is-scanning");

    try {
      const data = await EVForecast.API.login({
        email,
        password,
      });
      EVForecast.saveSession(data.token, data.user);

      try {
        if (els.remember?.checked) {
          localStorage.setItem("evforecast_remember_email", email);
        } else {
          localStorage.removeItem("evforecast_remember_email");
        }
      } catch (_) { /* ignore */ }

      els.card.classList.add("is-dissolving");
      els.success.classList.add("is-active");
      els.success.setAttribute("aria-hidden", "false");

      if (typeof gsap !== "undefined") {
        gsap.to(els.card, {
          scale: 1.08,
          opacity: 0,
          filter: "blur(12px)",
          duration: 1.0,
          ease: "power2.in",
        });
        gsap.to(els.root, {
          scale: 1.06,
          duration: 1.4,
          ease: "power2.inOut",
        });
      }

      const dest = data.user.role === "admin" ? "/admin" : "/dashboard";
      setTimeout(() => { location.href = dest; }, 1600);
    } catch (ex) {
      els.btn.classList.remove("is-loading");
      els.card.classList.remove("is-scanning");
      els.error.textContent = ex.data?.message || ex.message || "Login failed";
      els.error.classList.add("show");
    }
  });

  // Skip intro on click / Escape so login is always reachable
  function skipCinema() {
    if (!cinemaDone) revealWorkspace();
  }
  els.cinema?.addEventListener("click", skipCinema);
  window.addEventListener("keydown", (e) => {
    if (cinemaDone) return;
    if (e.key === "Escape" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      skipCinema();
    }
  });

  initThree();
  playCinema();
})();
