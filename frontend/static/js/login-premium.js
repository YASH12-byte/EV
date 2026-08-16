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
    actor: document.getElementById("lpActor"),
    humanCanvas: document.getElementById("lpHumanCanvas"),
    bagBurst: document.getElementById("lpBagBurst"),
    lab: document.querySelector(".lp-lab"),
    deskGlow: document.querySelector(".lp-desk-glow"),
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
  let human3d = null;
  const timers = [];

  function later(fn, ms) {
    const id = setTimeout(fn, ms);
    timers.push(id);
    return id;
  }

  function clearTimers() {
    while (timers.length) clearTimeout(timers.pop());
  }

  function revealWorkspace() {
    if (cinemaDone) return;
    cinemaDone = true;
    clearTimers();
    human3d?.setState("done");
    els.cinema?.classList.add("is-done");
    els.cinema?.classList.remove("is-walking", "is-throwing", "is-bag-open");
    els.workspace?.classList.add("is-visible");
    els.workspace?.setAttribute("aria-hidden", "false");
    setTimeout(() => {
      if (window.EVForecast?.enableCard3DTilt) {
        EVForecast.enableCard3DTilt("#lpCard");
      }
    }, 400);
  }

  /**
   * Sequence (must finish before login opens):
   * 1) 3D human walks in with bag
   * 2) Stop
   * 3) Throw bag onto desk
   * 4) Bag opens / burst
   * 5) Login page appears
   */
  function playCinema() {
    if (reduced) {
      later(revealWorkspace, 300);
      return;
    }

    const cinema = els.cinema;
    const actor = els.actor;
    if (!cinema) {
      later(revealWorkspace, 200);
      return;
    }

    if (window.EVHuman3D && els.humanCanvas) {
      human3d = EVHuman3D.create(els.humanCanvas);
    }

    els.workspace?.classList.remove("is-visible");
    els.workspace?.setAttribute("aria-hidden", "true");
    cinema.classList.remove("is-done", "is-walking", "is-throwing", "is-bag-open");

    // Scene 1 — 3D human walks in
    actor?.classList.add("is-walking");
    human3d?.setState("walk");
    requestAnimationFrame(() => {
      cinema.classList.add("is-walking");
      if (els.lab) els.lab.style.opacity = "1";
    });

    // Scene 2 — stop at desk
    later(() => {
      actor?.classList.remove("is-walking");
      human3d?.setState("idle");
    }, 3400);

    // Scene 3 — throw bag
    later(() => {
      cinema.classList.add("is-throwing");
      human3d?.setState("throw");
      if (els.deskGlow) els.deskGlow.style.opacity = "1";
    }, 4000);

    // Scene 4 — bag lands & opens
    later(() => {
      cinema.classList.remove("is-throwing");
      cinema.classList.add("is-bag-open");
      human3d?.setState("open");
    }, 5200);

    // Scene 5 — open login page
    later(() => {
      revealWorkspace();
    }, 6800);
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
      [0.145, 0.388, 0.922], // electric blue
      [0.024, 0.714, 0.831], // cyan
      [0.063, 0.725, 0.506], // emerald
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

    // Soft neural links (line segments)
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

  // Remember me
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

      // Success cinematic
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

  // Boot
  initThree();
  playCinema();
})();
