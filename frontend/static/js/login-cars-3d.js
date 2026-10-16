(() => {
  "use strict";

  /**
   * High-End 3D Luxury Electric Cars & Cinematic Security Gate Intro
   * Renders sculpted luxury EVs (Grand Coupe, Executive GT, Track Hypercar)
   * with metallic clearcoat paint, panoramic glass canopies, multi-spoke turbine rims,
   * high-performance brake calipers, LED matrix lightbars, forward headlight beams,
   * neon underglow, and physics-based wheel roll & suspension dynamics.
   */

  function createLuxuryCar(palette) {
    const group = new THREE.Group();

    // 1. Physically-based luxury automotive materials
    const bodyMat = new THREE.MeshStandardMaterial({
      color: palette.body,
      roughness: 0.16,
      metalness: 0.88,
      emissive: palette.emissive,
      emissiveIntensity: 0.18,
    });

    const carbonMat = new THREE.MeshStandardMaterial({
      color: 0x090f18,
      roughness: 0.38,
      metalness: 0.75,
    });

    const glassMat = new THREE.MeshStandardMaterial({
      color: 0x06111f,
      roughness: 0.05,
      metalness: 0.95,
      transparent: true,
      opacity: 0.84,
    });

    const headlightMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      emissive: palette.light,
      emissiveIntensity: 2.2,
      roughness: 0.1,
      metalness: 0.4,
    });

    const taillightMat = new THREE.MeshStandardMaterial({
      color: 0xff1e42,
      emissive: 0xff1e42,
      emissiveIntensity: 2.4,
      roughness: 0.15,
      metalness: 0.3,
    });

    const caliperMat = new THREE.MeshStandardMaterial({
      color: palette.caliper || 0x06b6d4,
      roughness: 0.22,
      metalness: 0.78,
      emissive: palette.caliper || 0x06b6d4,
      emissiveIntensity: 0.45,
    });

    const rimMat = new THREE.MeshStandardMaterial({
      color: palette.rim || 0xe2e8f0,
      roughness: 0.18,
      metalness: 0.92,
    });

    const tireMat = new THREE.MeshStandardMaterial({
      color: 0x11161f,
      roughness: 0.82,
      metalness: 0.12,
    });

    const discMat = new THREE.MeshStandardMaterial({
      color: 0x94a3b8,
      roughness: 0.28,
      metalness: 0.94,
    });

    // --- 2. Sculpted Luxury Chassis & Lower Aerodynamics ---
    // Main lower monocoque tub
    const chassis = new THREE.Mesh(new THREE.BoxGeometry(2.32, 0.22, 0.96), bodyMat);
    chassis.position.y = 0.25;
    chassis.castShadow = true;
    group.add(chassis);

    // Aerodynamic side skirts with recessed air intakes
    [-0.49, 0.49].forEach((z) => {
      const skirt = new THREE.Mesh(new THREE.BoxGeometry(1.58, 0.07, 0.08), carbonMat);
      skirt.position.set(0, 0.15, z);
      group.add(skirt);
    });

    // Front carbon aerodynamic splitter with winglets
    const frontSplitter = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.035, 1.02), carbonMat);
    frontSplitter.position.set(1.15, 0.13, 0);
    group.add(frontSplitter);

    [-0.51, 0.51].forEach((z) => {
      const winglet = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.09, 0.03), carbonMat);
      winglet.position.set(1.18, 0.17, z);
      group.add(winglet);
    });

    // Rear race diffuser with vertical strakes
    const rearDiffuser = new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.1, 0.98), carbonMat);
    rearDiffuser.position.set(-1.15, 0.18, 0);
    rearDiffuser.rotation.z = 0.08;
    group.add(rearDiffuser);

    [-0.32, -0.12, 0.12, 0.32].forEach((s) => {
      const fin = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.08, 0.02), carbonMat);
      fin.position.set(-1.17, 0.16, s);
      group.add(fin);
    });

    // --- 3. Sculpted Hood, Muscular Shoulders & Fastback Deck ---
    // Sloping luxury aerodynamic bonnet
    const hood = new THREE.Mesh(new THREE.BoxGeometry(0.86, 0.11, 0.92), bodyMat);
    hood.position.set(0.68, 0.37, 0);
    hood.rotation.z = -0.065;
    hood.castShadow = true;
    group.add(hood);

    // Front nose cone with closed aero electric grille
    const noseFascia = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.18, 0.94), carbonMat);
    noseFascia.position.set(1.11, 0.25, 0);
    group.add(noseFascia);

    // Muscular front wheel arches
    [-0.46, 0.46].forEach((z) => {
      const frontArch = new THREE.Mesh(new THREE.BoxGeometry(0.64, 0.14, 0.09), bodyMat);
      frontArch.position.set(0.64, 0.34, z);
      group.add(frontArch);
    });

    // Flared rear muscular sports haunches
    [-0.47, 0.47].forEach((z) => {
      const rearHaunch = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.18, 0.11), bodyMat);
      rearHaunch.position.set(-0.66, 0.35, z);
      group.add(rearHaunch);
    });

    // Rear deck lid & integrated ducktail aero spoiler
    const rearDeck = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.12, 0.92), bodyMat);
    rearDeck.position.set(-0.94, 0.37, 0);
    rearDeck.rotation.z = 0.055;
    group.add(rearDeck);

    const spoiler = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.035, 0.9), carbonMat);
    spoiler.position.set(-1.17, 0.43, 0);
    spoiler.rotation.z = 0.14;
    group.add(spoiler);

    // --- 4. Panoramic Glass Canopy (Greenhouse) ---
    // Central glass canopy
    const canopy = new THREE.Mesh(new THREE.BoxGeometry(1.22, 0.31, 0.8), glassMat);
    canopy.position.set(-0.06, 0.51, 0);
    canopy.castShadow = true;
    group.add(canopy);

    // Low-slung raked windshield
    const windshield = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.27, 0.78), glassMat);
    windshield.position.set(0.45, 0.45, 0);
    windshield.rotation.z = -0.58;
    group.add(windshield);

    // Fastback sloping rear window
    const rearWindow = new THREE.Mesh(new THREE.BoxGeometry(0.54, 0.25, 0.78), glassMat);
    rearWindow.position.set(-0.62, 0.45, 0);
    rearWindow.rotation.z = 0.52;
    group.add(rearWindow);

    // Gloss black panoramic roof spine
    const roof = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.03, 0.74), carbonMat);
    roof.position.set(-0.08, 0.67, 0);
    group.add(roof);

    // Minimalist digital camera side mirrors with LED turn indicators
    [-0.49, 0.49].forEach((z) => {
      const stem = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.03, 0.1), carbonMat);
      stem.position.set(0.32, 0.41, z);
      group.add(stem);

      const mirror = new THREE.Mesh(new THREE.BoxGeometry(0.13, 0.05, 0.08), bodyMat);
      mirror.position.set(0.34, 0.42, z * 1.18);
      group.add(mirror);

      const indicator = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.018, 0.015), headlightMat);
      indicator.position.set(0.35, 0.42, z * 1.22);
      group.add(indicator);
    });

    // Interior ambient cockpit glow
    const cockpitLight = new THREE.PointLight(palette.light, 0.4, 1.8);
    cockpitLight.position.set(0.1, 0.46, 0);
    group.add(cockpitLight);

    // --- 5. Signature Luxury EV Lighting ---
    // Full-width front cybernetic LED lightbar
    const frontLightbar = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.035, 0.88), headlightMat);
    frontLightbar.position.set(1.23, 0.3, 0);
    group.add(frontLightbar);

    // Dual jewel matrix LED projector headlights
    [-0.37, 0.37].forEach((z) => {
      const headlamp = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.065, 0.16), headlightMat);
      headlamp.position.set(1.19, 0.3, z);
      group.add(headlamp);
    });

    // Forward projected headlight road illumination beams
    [-0.32, 0.32].forEach((z) => {
      const beam = new THREE.Mesh(
        new THREE.ConeGeometry(0.55, 3.2, 16, 1, true),
        new THREE.MeshBasicMaterial({
          color: palette.light,
          transparent: true,
          opacity: 0.16,
          depthWrite: false,
          side: THREE.DoubleSide,
        })
      );
      beam.rotation.z = -Math.PI / 2;
      beam.rotation.x = z > 0 ? 0.05 : -0.05;
      beam.position.set(2.75, 0.14, z);
      group.add(beam);
    });

    // Full-width rear OLED laser red taillight bar
    const rearLightbar = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.035, 0.88), taillightMat);
    rearLightbar.position.set(-1.21, 0.33, 0);
    group.add(rearLightbar);

    // Diffuser center F1-style rain/brake strobe light
    const centerBrake = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.025, 0.14), taillightMat);
    centerBrake.position.set(-1.22, 0.17, 0);
    group.add(centerBrake);

    // Luxury Neon Underglow Ground Illumination
    const underGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(2.35, 1.15),
      new THREE.MeshBasicMaterial({
        color: palette.light,
        transparent: true,
        opacity: 0.42,
        side: THREE.DoubleSide,
        depthWrite: false,
      })
    );
    underGlow.rotation.x = -Math.PI / 2;
    underGlow.position.y = 0.02;
    group.add(underGlow);

    // --- 6. Detailed Multi-Piece Luxury Turbine Wheels ---
    const wheelRadius = 0.205;
    const wheelWidth = 0.125;
    const wheelGeo = new THREE.CylinderGeometry(wheelRadius, wheelRadius, wheelWidth, 24);
    const discGeo = new THREE.CylinderGeometry(0.14, 0.14, 0.02, 18);
    const caliperGeo = new THREE.BoxGeometry(0.06, 0.08, 0.04);

    const wheelHubs = [];
    const wheelCoords = [
      { x: 0.65, z: 0.49, isFront: true },
      { x: 0.65, z: -0.49, isFront: true },
      { x: -0.68, z: 0.49, isFront: false },
      { x: -0.68, z: -0.49, isFront: false },
    ];

    wheelCoords.forEach(({ x, z, isFront }) => {
      // Rotating wheel hub (tire + alloy turbine rim + rotor disc)
      const wheelHub = new THREE.Group();
      wheelHub.position.set(x, wheelRadius, z);

      // Performance rubber tire
      const tire = new THREE.Mesh(wheelGeo, tireMat);
      tire.rotation.x = Math.PI / 2;
      tire.castShadow = true;
      wheelHub.add(tire);

      // Machined rim outer ring
      const rimRing = new THREE.Mesh(
        new THREE.CylinderGeometry(wheelRadius * 0.88, wheelRadius * 0.88, wheelWidth + 0.006, 20),
        rimMat
      );
      rimRing.rotation.x = Math.PI / 2;
      wheelHub.add(rimRing);

      // Multi-blade aerodynamic turbine spokes
      for (let i = 0; i < 5; i++) {
        const angle = (i * Math.PI * 2) / 5;
        const spoke = new THREE.Mesh(
          new THREE.BoxGeometry(wheelRadius * 1.5, 0.024, wheelWidth + 0.008),
          rimMat
        );
        spoke.rotation.z = angle;
        wheelHub.add(spoke);
      }

      // Center cap with glowing luxury EV emblem
      const centerCap = new THREE.Mesh(
        new THREE.CylinderGeometry(0.045, 0.045, wheelWidth + 0.016, 16),
        headlightMat
      );
      centerCap.rotation.x = Math.PI / 2;
      wheelHub.add(centerCap);

      // Cross-drilled brake rotor disc
      const disc = new THREE.Mesh(discGeo, discMat);
      disc.rotation.x = Math.PI / 2;
      wheelHub.add(disc);

      group.add(wheelHub);
      wheelHubs.push({ hub: wheelHub, isFront });

      // Sport brake caliper mounted stationary to chassis (does NOT spin!)
      const caliper = new THREE.Mesh(caliperGeo, caliperMat);
      caliper.position.set(x, wheelRadius + 0.065, z + (z > 0 ? -0.03 : 0.03));
      group.add(caliper);
    });

    group.userData.wheelHubs = wheelHubs;
    group.userData.wheelRadius = wheelRadius;
    group.userData.baseY = 0;
    return group;
  }

  function createGateLeaf(side) {
    const leaf = new THREE.Group();
    const panel = new THREE.Mesh(
      new THREE.BoxGeometry(2.4, 3.2, 0.12),
      new THREE.MeshStandardMaterial({
        color: 0x0a1c32,
        roughness: 0.32,
        metalness: 0.65,
        emissive: 0x06182c,
        emissiveIntensity: 0.25,
      })
    );
    panel.castShadow = true;
    panel.receiveShadow = true;
    leaf.add(panel);

    const frame = new THREE.Mesh(
      new THREE.BoxGeometry(2.5, 3.3, 0.06),
      new THREE.MeshStandardMaterial({
        color: 0x06b6d4,
        roughness: 0.25,
        metalness: 0.85,
        emissive: 0x06b6d4,
        emissiveIntensity: 0.35,
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
          emissiveIntensity: 0.5,
          metalness: 0.9,
          roughness: 0.2,
        })
      );
      bar.position.set(0, -1.1 + i * 0.7, 0.08);
      leaf.add(bar);
    }

    const emblem = new THREE.Mesh(
      new THREE.CircleGeometry(0.3, 24),
      new THREE.MeshStandardMaterial({
        color: 0x2563eb,
        emissive: 0x38bdf8,
        emissiveIntensity: 0.65,
        metalness: 0.8,
        roughness: 0.2,
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
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 140);
    // Dynamic 3/4 cinematic automotive showcase perspective
    camera.position.set(-1.8, 3.4, 9.8);
    camera.lookAt(0.2, 1.3, 0);

    // Studio Lighting for metallic paint reflections
    scene.add(new THREE.HemisphereLight(0xdbeafe, 0x050c16, 0.85));

    const sunKey = new THREE.DirectionalLight(0xffffff, 1.25);
    sunKey.position.set(5, 9, 7);
    sunKey.castShadow = true;
    sunKey.shadow.mapSize.set(1024, 1024);
    sunKey.shadow.bias = -0.0005;
    scene.add(sunKey);

    const iceRim = new THREE.DirectionalLight(0x38bdf8, 0.85);
    iceRim.position.set(-7, 4, -4);
    scene.add(iceRim);

    const warmFill = new THREE.PointLight(0x06b6d4, 0.75, 35);
    warmFill.position.set(0, 2.8, 4.5);
    scene.add(warmFill);

    // Highway Road Surface
    const road = new THREE.Mesh(
      new THREE.PlaneGeometry(38, 18),
      new THREE.MeshStandardMaterial({
        color: 0x08111e,
        roughness: 0.88,
        metalness: 0.15,
      })
    );
    road.rotation.x = -Math.PI / 2;
    road.receiveShadow = true;
    scene.add(road);

    // Glowing Road Lane Lines
    const laneMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, transparent: true, opacity: 0.65 });
    for (let i = -7; i <= 6; i++) {
      [-0.85, 0.85].forEach((zPos) => {
        const dash = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.08), laneMat);
        dash.rotation.x = -Math.PI / 2;
        dash.position.set(i * 2.6, 0.015, zPos);
        scene.add(dash);
      });
    }

    // Outer Runway Shoulders with neon runway beacons
    [-2.8, 2.8].forEach((zEdge) => {
      const edgeLine = new THREE.Mesh(new THREE.PlaneGeometry(36, 0.06), laneMat);
      edgeLine.rotation.x = -Math.PI / 2;
      edgeLine.position.set(0, 0.016, zEdge);
      scene.add(edgeLine);

      for (let bx = -8; bx <= 8; bx += 3.2) {
        const beacon = new THREE.Mesh(
          new THREE.CylinderGeometry(0.04, 0.04, 0.12, 12),
          new THREE.MeshBasicMaterial({ color: 0x38bdf8 })
        );
        beacon.position.set(bx, 0.06, zEdge);
        scene.add(beacon);
      }
    });

    // Grand Cybernetic Security Gate Arch
    const postMat = new THREE.MeshStandardMaterial({
      color: 0x112740,
      roughness: 0.35,
      metalness: 0.65,
      emissive: 0x081c30,
      emissiveIntensity: 0.3,
    });

    [-2.75, 2.75].forEach((z) => {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.4, 3.8, 0.4), postMat);
      post.position.set(0, 1.9, z);
      post.castShadow = true;
      scene.add(post);

      const pCap = new THREE.Mesh(new THREE.BoxGeometry(0.48, 0.08, 0.48), laneMat);
      pCap.position.set(0, 3.84, z);
      scene.add(pCap);
    });

    const arch = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.32, 5.9), postMat);
    arch.position.set(0, 3.8, 0);
    scene.add(arch);

    const archGlow = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.06, 5.4), laneMat);
    archGlow.position.set(0, 3.65, 0);
    scene.add(archGlow);

    const gateRoot = new THREE.Group();
    gateRoot.position.set(0, 1.6, 0);
    scene.add(gateRoot);

    const leftGate = createGateLeaf(-1);
    leftGate.scale.y = 0.5;
    leftGate.position.y = 0.8;
    leftGate.rotation.y = Math.PI / 2;
    gateRoot.add(leftGate);

    const rightGate = createGateLeaf(1);
    rightGate.scale.y = 0.5;
    rightGate.position.y = -0.8;
    rightGate.rotation.y = Math.PI / 2;
    gateRoot.add(rightGate);

    const portalGlow = new THREE.Mesh(
      new THREE.PlaneGeometry(0.1, 3.2),
      new THREE.MeshBasicMaterial({
        color: 0x06b6d4,
        transparent: true,
        opacity: 0,
        side: THREE.DoubleSide,
      })
    );
    portalGlow.position.set(0.05, 1.6, 0);
    portalGlow.rotation.y = Math.PI / 2;
    scene.add(portalGlow);

    // Fleet of 3 High-Performance Luxury Electric Vehicles
    const cars = [
      {
        name: "Apex Grand Coupe (Midnight Sapphire)",
        mesh: createLuxuryCar({
          body: 0x1d4ed8,
          emissive: 0x0284c7,
          light: 0x38bdf8,
          caliper: 0x06b6d4,
          rim: 0xf1f5f9,
        }),
        startX: -10.5,
        targetApproachX: -1.75,
        passX: 5.8,
        z: 0.35,
        scale: 1.0,
        speed: 2.65,
        prevX: -10.5,
      },
      {
        name: "Starlight Executive GT (Liquid Platinum)",
        mesh: createLuxuryCar({
          body: 0x334155,
          emissive: 0x64748b,
          light: 0x67e8f9,
          caliper: 0xf59e0b,
          rim: 0xe2e8f0,
        }),
        startX: -12.4,
        targetApproachX: -2.85,
        passX: 4.8,
        z: -1.25,
        scale: 0.94,
        speed: 2.35,
        prevX: -12.4,
      },
      {
        name: "Veloce Hypercar (Racing Emerald Pearl)",
        mesh: createLuxuryCar({
          body: 0x065f46,
          emissive: 0x059669,
          light: 0x34d399,
          caliper: 0xef4444,
          rim: 0x94a3b8,
        }),
        startX: -11.6,
        targetApproachX: -2.25,
        passX: 5.4,
        z: 1.75,
        scale: 0.92,
        speed: 2.85,
        prevX: -11.6,
      },
    ];

    cars.forEach((c) => {
      c.mesh.position.set(c.startX, 0, c.z);
      c.mesh.scale.setScalar(c.scale);
      // Car is facing along +X (forward down highway through gate)
      c.mesh.rotation.y = 0;
      scene.add(c.mesh);
    });

    let state = "idle"; // approach | open | done
    let openT = 0;
    let running = true;
    const clock = new THREE.Clock();
    const leftClosedY = 0.8;
    const rightClosedY = -0.8;
    const leftOpenY = 2.8;
    const rightOpenY = -2.8;

    // Mouse parallax tracking
    let mouseTargetX = 0;
    let mouseTargetY = 0;
    let mouseCurX = 0;
    let mouseCurY = 0;

    window.addEventListener("pointermove", (e) => {
      const nx = (e.clientX / window.innerWidth) * 2 - 1;
      const ny = (e.clientY / window.innerHeight) * 2 - 1;
      mouseTargetX = nx * 0.45;
      mouseTargetY = ny * 0.3;
    }, { passive: true });

    function resize() {
      const parent = canvas.parentElement;
      const w = (parent && parent.clientWidth) || window.innerWidth;
      const h = (parent && parent.clientHeight) || window.innerHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
    resize();
    window.addEventListener("resize", resize);

    function updateWheelsAndSuspension(car, dt, velocity, isAccelerating) {
      const mesh = car.mesh;
      const radius = mesh.userData.wheelRadius || 0.205;
      const rollAngle = (velocity * dt) / radius;

      // Realistic wheel spin around transverse Z-axis
      if (mesh.userData.wheelHubs) {
        mesh.userData.wheelHubs.forEach((w) => {
          w.hub.rotation.z -= rollAngle;
        });
      }

      // Subtle suspension micro-bounce and chassis dynamics
      const t = clock.elapsedTime * 9 + car.z;
      const bounce = Math.sin(t) * 0.005;
      mesh.position.y = bounce;

      // Dynamic pitch: slight squat on acceleration, slight dive on braking
      const targetPitch = isAccelerating ? -0.025 : 0.015 * Math.min(1, velocity * 0.5);
      mesh.rotation.z = THREE.MathUtils.lerp(mesh.rotation.z, targetPitch, dt * 4);
    }

    function animateApproach(dt) {
      cars.forEach((c) => {
        const oldX = c.mesh.position.x;
        c.mesh.position.x = THREE.MathUtils.lerp(c.mesh.position.x, c.targetApproachX, dt * (c.speed * 0.45));
        const velocity = Math.max(0, (c.mesh.position.x - oldX) / Math.max(dt, 0.001));
        updateWheelsAndSuspension(c, dt, velocity, false);
      });

      // Camera smooth tracking with gentle 3D parallax
      mouseCurX += (mouseTargetX - mouseCurX) * 0.06;
      mouseCurY += (mouseTargetY - mouseCurY) * 0.06;

      camera.position.x = THREE.MathUtils.lerp(camera.position.x, -1.8 + mouseCurX, dt * 1.2);
      camera.position.y = THREE.MathUtils.lerp(camera.position.y, 3.4 - mouseCurY, dt * 1.2);
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 9.2, dt * 0.8);
      camera.lookAt(0.3, 1.3, 0);
    }

    function animateOpen(dt) {
      openT += dt;
      const k = Math.min(1, openT / 1.45);
      const ease = 1 - Math.pow(1 - k, 3);

      // Gate leaves slide apart smoothly
      leftGate.position.y = THREE.MathUtils.lerp(leftClosedY, leftOpenY, ease);
      rightGate.position.y = THREE.MathUtils.lerp(rightClosedY, rightOpenY, ease);
      leftGate.rotation.y = Math.PI / 2 + THREE.MathUtils.lerp(0, -0.3, ease);
      rightGate.rotation.y = Math.PI / 2 + THREE.MathUtils.lerp(0, 0.3, ease);

      portalGlow.material.opacity = Math.sin(k * Math.PI) * 0.65 + (k > 0.4 ? 0.25 : 0);

      cars.forEach((c, idx) => {
        const oldX = c.mesh.position.x;
        const surge = k > 0.35 ? Math.pow(k - 0.35, 1.8) * 12 : 0;
        c.mesh.position.x = THREE.MathUtils.lerp(c.mesh.position.x, c.passX + surge + idx * 0.4, dt * 2.2);
        const velocity = Math.max(0, (c.mesh.position.x - oldX) / Math.max(dt, 0.001));
        updateWheelsAndSuspension(c, dt, velocity, true);
      });

      camera.position.x = THREE.MathUtils.lerp(camera.position.x, 0.6 + mouseCurX, dt * 1.4);
      camera.position.y = THREE.MathUtils.lerp(camera.position.y, 2.7 - mouseCurY, dt * 1.2);
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, 7.6, dt * 1.4);
      camera.lookAt(1.4, 1.3, 0);
    }

    function tick() {
      if (!running) return;
      const dt = Math.min(0.033, clock.getDelta());
      if (state === "approach") animateApproach(dt);
      else if (state === "open") animateOpen(dt);
      else if (state === "done") {
        portalGlow.material.opacity = Math.max(0, portalGlow.material.opacity - dt * 2);
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
          leftGate.position.y = leftClosedY;
          rightGate.position.y = rightClosedY;
          leftGate.rotation.y = Math.PI / 2;
          rightGate.rotation.y = Math.PI / 2;
          cars.forEach((c) => {
            c.mesh.visible = true;
            c.mesh.position.x = c.startX;
            c.mesh.rotation.z = 0;
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
