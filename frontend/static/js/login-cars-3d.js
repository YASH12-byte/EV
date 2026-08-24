(() => {
  "use strict";

  /**
   * Cinematic intro: 3D EVs approach a closed gate → gate opens → unlock login.
   */
  function createCar(palette) {
    const group = new THREE.Group();
    const bodyMat = new THREE.MeshStandardMaterial({
      color: palette.body,
      roughness: 0.28,
      metalness: 0.72,
      emissive: palette.emissive,
      emissiveIntensity: 0.22,
    });
    const darkMat = new THREE.MeshStandardMaterial({
      color: 0x0a1524,
      roughness: 0.4,
      metalness: 0.55,
    });
    const glassMat = new THREE.MeshStandardMaterial({
      color: 0x1e3a5f,
      roughness: 0.15,
      metalness: 0.85,
      transparent: true,
      opacity: 0.75,
    });
    const lightMat = new THREE.MeshStandardMaterial({
      color: palette.light,
      emissive: palette.light,
      emissiveIntensity: 0.9,
      roughness: 0.3,
      metalness: 0.4,
    });

    const body = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.38, 0.85), bodyMat);
    body.position.y = 0.38;
    body.castShadow = true;
    group.add(body);

    const cabin = new THREE.Mesh(new THREE.BoxGeometry(0.85, 0.32, 0.78), glassMat);
    cabin.position.set(-0.12, 0.68, 0);
    cabin.castShadow = true;
    group.add(cabin);

    const hood = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.12, 0.82), bodyMat);
    hood.position.set(0.52, 0.52, 0);
    group.add(hood);

    const bumper = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.16, 0.86), darkMat);
    bumper.position.set(0.88, 0.3, 0);
    group.add(bumper);

    [[0.78, 0.32, 0.38], [0.78, 0.32, -0.38]].forEach(([x, y, z]) => {
      const light = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.1, 0.14), lightMat);
      light.position.set(x, y, z);
      group.add(light);
    });

    [[-0.72, 0.32, 0.38], [-0.72, 0.32, -0.38]].forEach(([x, y, z]) => {
      const light = new THREE.Mesh(
        new THREE.BoxGeometry(0.05, 0.08, 0.12),
        new THREE.MeshStandardMaterial({
          color: 0xef4444,
          emissive: 0xef4444,
          emissiveIntensity: 0.55,
        })
      );
      light.position.set(x, y, z);
      group.add(light);
    });

    const wheelGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.12, 16);
    const wheelMat = new THREE.MeshStandardMaterial({
      color: 0x111827,
      roughness: 0.7,
      metalness: 0.2,
    });
    const rimMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      roughness: 0.35,
      metalness: 0.85,
    });

    [
      [0.48, 0.18, 0.48],
      [0.48, 0.18, -0.48],
      [-0.48, 0.18, 0.48],
      [-0.48, 0.18, -0.48],
    ].forEach(([x, y, z]) => {
      const wheel = new THREE.Mesh(wheelGeo, wheelMat);
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(x, y, z);
      wheel.castShadow = true;
      group.add(wheel);
      const rim = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.13, 12), rimMat);
      rim.rotation.z = Math.PI / 2;
      rim.position.set(x, y, z);
      group.add(rim);
      wheel.userData.spin = true;
    });

    const underGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(1.5, 0.7),
      new THREE.MeshBasicMaterial({
        color: palette.light,
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
      })
    );
    underGlow.rotation.x = -Math.PI / 2;
    underGlow.position.y = 0.02;
    group.add(underGlow);

    group.userData.wheels = group.children.filter((c) => c.userData.spin);
    return group;
  }

  function createGateLeaf(side) {
    const leaf = new THREE.Group();
    const panel = new THREE.Mesh(
      new THREE.BoxGeometry(2.4, 3.2, 0.12),
      new THREE.MeshStandardMaterial({
        color: 0x0f2744,
        roughness: 0.35,
        metalness: 0.55,
        emissive: 0x06203a,
        emissiveIntensity: 0.2,
      })
    );
    panel.castShadow = true;
    panel.receiveShadow = true;
    leaf.add(panel);

    const frame = new THREE.Mesh(
      new THREE.BoxGeometry(2.5, 3.3, 0.06),
      new THREE.MeshStandardMaterial({
        color: 0x06b6d4,
        roughness: 0.3,
        metalness: 0.8,
        emissive: 0x06b6d4,
        emissiveIntensity: 0.25,
      })
    );
    frame.position.z = 0.02;
    leaf.add(frame);

    for (let i = 0; i < 4; i++) {
      const bar = new THREE.Mesh(
        new THREE.BoxGeometry(2.1, 0.04, 0.04),
        new THREE.MeshStandardMaterial({
          color: 0x38bdf8,
          emissive: 0x2563eb,
          emissiveIntensity: 0.4,
          metalness: 0.9,
          roughness: 0.2,
        })
      );
      bar.position.set(0, -1.1 + i * 0.7, 0.08);
      leaf.add(bar);
    }

    const emblem = new THREE.Mesh(
      new THREE.CircleGeometry(0.28, 24),
      new THREE.MeshStandardMaterial({
        color: 0x2563eb,
        emissive: 0x2563eb,
        emissiveIntensity: 0.55,
        metalness: 0.7,
        roughness: 0.25,
      })
    );
    emblem.position.set(side * -0.55, 0.35, 0.1);
    leaf.add(emblem);

    return leaf;
  }

  function createCars3D(canvas) {
    if (!canvas || typeof THREE === "undefined") return null;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    if (renderer.outputEncoding !== undefined) {
      renderer.outputEncoding = THREE.sRGBEncoding;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 120);
    camera.position.set(0, 3.2, 11.5);
    camera.lookAt(0, 1.4, 0);

    scene.add(new THREE.HemisphereLight(0xb8d4ff, 0x081018, 0.75));
    const key = new THREE.DirectionalLight(0xffffff, 1.05);
    key.position.set(4, 8, 6);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x38bdf8, 0.5);
    rim.position.set(-5, 3, -3);
    scene.add(rim);
    const fill = new THREE.PointLight(0x06b6d4, 0.55, 28);
    fill.position.set(0, 2.5, 4);
    scene.add(fill);

    const road = new THREE.Mesh(
      new THREE.PlaneGeometry(28, 18),
      new THREE.MeshStandardMaterial({ color: 0x0a1422, roughness: 0.95, metalness: 0.05 })
    );
    road.rotation.x = -Math.PI / 2;
    road.receiveShadow = true;
    scene.add(road);

    const laneMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.55 });
    for (let i = -4; i <= 2; i++) {
      const dash = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.08), laneMat);
      dash.rotation.x = -Math.PI / 2;
      dash.position.set(i * 2.4, 0.015, 0);
      scene.add(dash);
    }

    // Gate posts + arch
    const postMat = new THREE.MeshStandardMaterial({
      color: 0x16304a,
      roughness: 0.4,
      metalness: 0.5,
      emissive: 0x0a2038,
      emissiveIntensity: 0.3,
    });
    [-2.55, 2.55].forEach((x) => {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.35, 3.6, 0.35), postMat);
      post.position.set(x, 1.8, -1.2);
      post.castShadow = true;
      scene.add(post);
    });
    const arch = new THREE.Mesh(new THREE.BoxGeometry(5.5, 0.28, 0.35), postMat);
    arch.position.set(0, 3.5, -1.2);
    scene.add(arch);

    const gateRoot = new THREE.Group();
    gateRoot.position.set(0, 1.6, -1.2);
    scene.add(gateRoot);

    const leftGate = createGateLeaf(-1);
    leftGate.position.x = -1.2;
    gateRoot.add(leftGate);
    const rightGate = createGateLeaf(1);
    rightGate.position.x = 1.2;
    gateRoot.add(rightGate);

    const portalGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(4.6, 3.1),
      new THREE.MeshBasicMaterial({
        color: 0x2563eb,
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
      })
    );
    portalGlow.position.set(0, 1.55, -1.05);
    scene.add(portalGlow);

    const cars = [
      {
        mesh: createCar({ body: 0x2563eb, emissive: 0x0b2a66, light: 0x38bdf8 }),
        startX: -9.5,
        z: 1.1,
        scale: 1,
        speed: 2.4,
      },
      {
        mesh: createCar({ body: 0x06b6d4, emissive: 0x064e5a, light: 0x67e8f9 }),
        startX: -11.2,
        z: -0.15,
        scale: 0.92,
        speed: 2.15,
      },
      {
        mesh: createCar({ body: 0x10b981, emissive: 0x064e3b, light: 0x34d399 }),
        startX: -10.4,
        z: 2.15,
        scale: 0.88,
        speed: 2.55,
      },
    ];

    cars.forEach((c) => {
      c.mesh.position.set(c.startX, 0, c.z);
      c.mesh.scale.setScalar(c.scale);
      c.mesh.rotation.y = Math.PI / 2;
      scene.add(c.mesh);
    });

    let state = "idle"; // approach | open | done
    let openT = 0;
    let running = true;
    const clock = new THREE.Clock();
    const leftClosed = -1.2;
    const rightClosed = 1.2;
    const leftOpen = -3.35;
    const rightOpen = 3.35;

    function resize() {
      const parent = canvas.parentElement;
      const w = parent?.clientWidth || window.innerWidth;
      const h = parent?.clientHeight || window.innerHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
    resize();
    window.addEventListener("resize", resize);

    function animateApproach(dt) {
      cars.forEach((c) => {
        const target = c.z > 1.5 ? -3.2 : c.z < 0.5 ? -2.4 : -1.6;
        c.mesh.position.x = THREE.MathUtils.lerp(c.mesh.position.x, target, dt * (c.speed * 0.35));
        c.mesh.userData.wheels?.forEach((w) => {
          w.rotation.x += dt * 14;
        });
        c.mesh.position.y = Math.sin(clock.elapsedTime * 10 + c.z) * 0.008;
      });
      camera.position.x = THREE.MathUtils.lerp(camera.position.x, 0.4, dt * 1.2);
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 9.2, dt * 0.8);
      camera.lookAt(0, 1.5, -1);
    }

    function animateOpen(dt) {
      openT += dt;
      const k = Math.min(1, openT / 1.35);
      const e = 1 - Math.pow(1 - k, 3);
      leftGate.position.x = THREE.MathUtils.lerp(leftClosed, leftOpen, e);
      rightGate.position.x = THREE.MathUtils.lerp(rightClosed, rightOpen, e);
      leftGate.rotation.y = THREE.MathUtils.lerp(0, -0.35, e);
      rightGate.rotation.y = THREE.MathUtils.lerp(0, 0.35, e);
      portalGlow.material.opacity = Math.sin(k * Math.PI) * 0.55 + (k > 0.4 ? 0.2 : 0);

      cars.forEach((c, i) => {
        const push = k > 0.45 ? (k - 0.45) * 6 : 0;
        c.mesh.position.x = THREE.MathUtils.lerp(c.mesh.position.x, 1.2 + push + i * 0.35, dt * 1.8);
        c.mesh.userData.wheels?.forEach((w) => {
          w.rotation.x += dt * (8 + push * 4);
        });
      });

      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 7.2, dt * 1.5);
      camera.position.y = THREE.MathUtils.lerp(camera.position.y, 2.6, dt * 1.2);
      camera.lookAt(0, 1.6, -1);
    }

    function tick() {
      if (!running) return;
      const dt = Math.min(0.033, clock.getDelta());
      if (state === "approach") animateApproach(dt);
      else if (state === "open") animateOpen(dt);
      else if (state === "done") {
        portalGlow.material.opacity = Math.max(0, portalGlow.material.opacity - dt);
      }
      renderer.render(scene, camera);
      requestAnimationFrame(tick);
    }
    tick();

    return {
      setState(next) {
        state = next;
        if (next === "approach") {
          openT = 0;
          leftGate.position.x = leftClosed;
          rightGate.position.x = rightClosed;
          leftGate.rotation.y = 0;
          rightGate.rotation.y = 0;
          cars.forEach((c) => {
            c.mesh.visible = true;
            c.mesh.position.x = c.startX;
          });
          portalGlow.material.opacity = 0;
        }
        if (next === "open") openT = 0;
        if (next === "done") {
          running = false;
        }
      },
      destroy() {
        running = false;
        renderer.dispose();
      },
      resize,
    };
  }

  window.EVCars3D = { create: createCars3D };
})();
