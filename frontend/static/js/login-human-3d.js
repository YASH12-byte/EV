(() => {
  "use strict";

  /**
   * Real 3D humanoid for cinematic intro.
   * Walk → stop → throw bag → unlock login.
   */
  function createHuman3D(canvas) {
    if (!canvas || typeof THREE === "undefined") return null;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputEncoding = THREE.sRGBEncoding;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
    camera.position.set(0.55, 1.55, 5.2);
    camera.lookAt(0, 1.05, 0);

    // Lights for realistic form
    const hemi = new THREE.HemisphereLight(0xb8d4ff, 0x0a1524, 0.85);
    scene.add(hemi);
    const key = new THREE.DirectionalLight(0xffffff, 1.15);
    key.position.set(3.5, 6, 4);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.near = 0.5;
    key.shadow.camera.far = 20;
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x38bdf8, 0.55);
    rim.position.set(-4, 2.5, -2);
    scene.add(rim);
    const fill = new THREE.PointLight(0x06b6d4, 0.45, 12);
    fill.position.set(-1.5, 1.8, 2.5);
    scene.add(fill);

    // Floor shadow catcher
    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(1.6, 48),
      new THREE.ShadowMaterial({ opacity: 0.45 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = 0;
    floor.receiveShadow = true;
    scene.add(floor);

    // Soft ground glow
    const glow = new THREE.Mesh(
      new THREE.CircleGeometry(1.1, 32),
      new THREE.MeshBasicMaterial({
        color: 0x2563eb,
        transparent: true,
        opacity: 0.18,
      })
    );
    glow.rotation.x = -Math.PI / 2;
    glow.position.y = 0.01;
    scene.add(glow);

    const skin = new THREE.MeshStandardMaterial({
      color: 0xd4a574,
      roughness: 0.55,
      metalness: 0.05,
    });
    const skinDark = new THREE.MeshStandardMaterial({
      color: 0xc49262,
      roughness: 0.6,
      metalness: 0.04,
    });
    const suit = new THREE.MeshStandardMaterial({
      color: 0x1a3350,
      roughness: 0.42,
      metalness: 0.25,
    });
    const suitDark = new THREE.MeshStandardMaterial({
      color: 0x0f2438,
      roughness: 0.4,
      metalness: 0.3,
    });
    const hairMat = new THREE.MeshStandardMaterial({
      color: 0x1a1f2b,
      roughness: 0.85,
      metalness: 0.05,
    });
    const shoeMat = new THREE.MeshStandardMaterial({
      color: 0x0a1018,
      roughness: 0.35,
      metalness: 0.4,
    });
    const bagMat = new THREE.MeshStandardMaterial({
      color: 0x16304a,
      roughness: 0.35,
      metalness: 0.45,
      emissive: 0x06203a,
      emissiveIntensity: 0.25,
    });
    const accentMat = new THREE.MeshStandardMaterial({
      color: 0x06b6d4,
      roughness: 0.3,
      metalness: 0.7,
      emissive: 0x06b6d4,
      emissiveIntensity: 0.35,
    });

    function part(geo, mat, cast = true) {
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = cast;
      m.receiveShadow = true;
      return m;
    }

    const root = new THREE.Group();
    root.position.set(-3.6, 0, 0);
    scene.add(root);

    // Hips / torso
    const hips = new THREE.Group();
    hips.position.y = 0.95;
    root.add(hips);

    const torso = part(new THREE.BoxGeometry(0.42, 0.58, 0.24), suit);
    torso.position.y = 0.28;
    hips.add(torso);
    const torsoFront = part(new THREE.BoxGeometry(0.18, 0.42, 0.02), suitDark, false);
    torsoFront.position.set(0, 0.28, 0.125);
    hips.add(torsoFront);
    const collar = part(new THREE.TorusGeometry(0.09, 0.018, 8, 20, Math.PI), accentMat, false);
    collar.rotation.x = Math.PI / 2;
    collar.position.set(0, 0.54, 0.02);
    hips.add(collar);

    // Head
    const neck = part(new THREE.CylinderGeometry(0.05, 0.06, 0.1, 12), skin);
    neck.position.y = 0.62;
    hips.add(neck);

    const head = new THREE.Group();
    head.position.y = 0.78;
    hips.add(head);
    const skull = part(new THREE.SphereGeometry(0.155, 24, 20), skin);
    skull.scale.set(1, 1.12, 0.95);
    head.add(skull);
    const hair = part(new THREE.SphereGeometry(0.16, 20, 16, 0, Math.PI * 2, 0, Math.PI * 0.55), hairMat);
    hair.position.y = 0.04;
    head.add(hair);
    const bang = part(new THREE.BoxGeometry(0.26, 0.05, 0.08), hairMat, false);
    bang.position.set(0, 0.1, 0.1);
    bang.rotation.x = -0.35;
    head.add(bang);
    const eyeGeo = new THREE.SphereGeometry(0.018, 10, 10);
    const eyeMat = new THREE.MeshStandardMaterial({ color: 0x1a2332, roughness: 0.3 });
    const eyeL = part(eyeGeo, eyeMat, false);
    eyeL.position.set(-0.05, 0.02, 0.13);
    const eyeR = part(eyeGeo, eyeMat, false);
    eyeR.position.set(0.05, 0.02, 0.13);
    head.add(eyeL, eyeR);
    const nose = part(new THREE.ConeGeometry(0.015, 0.04, 8), skinDark, false);
    nose.rotation.x = Math.PI / 2;
    nose.position.set(0, -0.01, 0.145);
    head.add(nose);

    function limb(radius, length, mat) {
      return part(new THREE.CylinderGeometry(radius, radius * 0.95, length, 12), mat);
    }

    // Arms
    function makeArm(side) {
      const shoulder = new THREE.Group();
      shoulder.position.set(side * 0.26, 0.5, 0);
      hips.add(shoulder);

      const upper = limb(0.055, 0.28, suit);
      upper.position.y = -0.16;
      shoulder.add(upper);

      const elbow = new THREE.Group();
      elbow.position.y = -0.32;
      shoulder.add(elbow);

      const forearm = limb(0.045, 0.26, suit);
      forearm.position.y = -0.14;
      elbow.add(forearm);

      const hand = part(new THREE.SphereGeometry(0.05, 12, 12), skin);
      hand.position.y = -0.3;
      elbow.add(hand);

      return { shoulder, elbow, hand };
    }

    const armL = makeArm(-1);
    const armR = makeArm(1);

    // Bag in right hand
    const bag = new THREE.Group();
    bag.position.set(0.02, -0.08, 0.02);
    armR.hand.add(bag);
    const bagBody = part(new THREE.BoxGeometry(0.22, 0.16, 0.1), bagMat);
    bagBody.position.y = -0.02;
    bag.add(bagBody);
    const bagLid = part(new THREE.BoxGeometry(0.23, 0.04, 0.11), suitDark);
    bagLid.position.y = 0.08;
    bag.add(bagLid);
    const bagHandle = part(new THREE.TorusGeometry(0.05, 0.01, 6, 16, Math.PI), accentMat, false);
    bagHandle.rotation.z = Math.PI / 2;
    bagHandle.position.y = 0.13;
    bag.add(bagHandle);
    const bagGlow = part(
      new THREE.BoxGeometry(0.18, 0.02, 0.02),
      new THREE.MeshBasicMaterial({ color: 0x06b6d4 }),
      false
    );
    bagGlow.position.set(0, 0, 0.055);
    bag.add(bagGlow);

    // Detached bag for throw flight
    const flyBag = bag.clone(true);
    flyBag.visible = false;
    scene.add(flyBag);

    // Legs
    function makeLeg(side) {
      const hip = new THREE.Group();
      hip.position.set(side * 0.1, 0, 0);
      root.add(hip);

      const thigh = limb(0.07, 0.34, suitDark);
      thigh.position.y = -0.22;
      hip.add(thigh);

      const knee = new THREE.Group();
      knee.position.y = -0.44;
      hip.add(knee);

      const shin = limb(0.055, 0.34, suitDark);
      shin.position.y = -0.2;
      knee.add(shin);

      const shoe = part(new THREE.BoxGeometry(0.12, 0.06, 0.22), shoeMat);
      shoe.position.set(0, -0.4, 0.04);
      knee.add(shoe);

      return { hip, knee };
    }

    const legL = makeLeg(-1);
    const legR = makeLeg(1);

    // Desk target marker (invisible)
    const deskPos = new THREE.Vector3(0.85, 0.95, 0.2);

    let state = "idle"; // walk | idle | throw | open | done
    let walkPhase = 0;
    let throwT = 0;
    let openT = 0;
    const clock = new THREE.Clock();
    let running = true;

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

    function setPoseIdle() {
      armL.shoulder.rotation.set(0.15, 0, 0.12);
      armL.elbow.rotation.set(-0.25, 0, 0);
      armR.shoulder.rotation.set(0.2, 0, -0.2);
      armR.elbow.rotation.set(-0.35, 0, 0);
      legL.hip.rotation.set(0, 0, 0);
      legL.knee.rotation.set(0, 0, 0);
      legR.hip.rotation.set(0, 0, 0);
      legR.knee.rotation.set(0, 0, 0);
      hips.rotation.z = 0;
      root.rotation.y = 0.35;
    }

    function animateWalk(dt) {
      walkPhase += dt * 8.5;
      const s = Math.sin(walkPhase);
      const c = Math.cos(walkPhase);
      legL.hip.rotation.x = s * 0.55;
      legR.hip.rotation.x = -s * 0.55;
      legL.knee.rotation.x = Math.max(0, -s) * 0.7;
      legR.knee.rotation.x = Math.max(0, s) * 0.7;
      armL.shoulder.rotation.x = -s * 0.45;
      armR.shoulder.rotation.x = s * 0.35;
      armL.elbow.rotation.x = -0.4 + Math.abs(s) * 0.2;
      armR.elbow.rotation.x = -0.5;
      hips.position.y = 0.95 + Math.abs(c) * 0.03;
      hips.rotation.z = s * 0.04;
      root.position.y = Math.abs(c) * 0.02;
      // walk toward center
      root.position.x = THREE.MathUtils.lerp(root.position.x, -0.15, dt * 0.55);
      root.rotation.y = THREE.MathUtils.lerp(root.rotation.y, 0.15, dt * 0.8);
      camera.position.x = THREE.MathUtils.lerp(camera.position.x, root.position.x + 0.7, dt * 1.2);
    }

    function animateThrow(dt) {
      throwT += dt;
      const t = throwT;
      if (t < 0.35) {
        // wind up
        const k = t / 0.35;
        armR.shoulder.rotation.x = THREE.MathUtils.lerp(0.2, -1.1, k);
        armR.elbow.rotation.x = THREE.MathUtils.lerp(-0.35, -0.2, k);
      } else if (t < 0.75) {
        // release
        const k = (t - 0.35) / 0.4;
        armR.shoulder.rotation.x = THREE.MathUtils.lerp(-1.1, 0.85, k);
        armR.elbow.rotation.x = THREE.MathUtils.lerp(-0.2, -0.55, k);
          if (k > 0.35 && bag.visible) {
            bag.visible = false;
            flyBag.visible = true;
            const wp = new THREE.Vector3();
            const wq = new THREE.Quaternion();
            armR.hand.getWorldPosition(wp);
            armR.hand.getWorldQuaternion(wq);
            flyBag.position.copy(wp);
            flyBag.quaternion.copy(wq);
            flyBag.userData.start = wp.clone();
            flyBag.userData.t = 0;
          }
      } else {
        armR.shoulder.rotation.x = THREE.MathUtils.lerp(armR.shoulder.rotation.x, 0.25, dt * 4);
      }

      if (flyBag.visible && flyBag.userData.start) {
        flyBag.userData.t += dt;
        const u = Math.min(1, flyBag.userData.t / 0.85);
        const start = flyBag.userData.start;
        flyBag.position.x = THREE.MathUtils.lerp(start.x, deskPos.x, u);
        flyBag.position.z = THREE.MathUtils.lerp(start.z, deskPos.z, u);
        flyBag.position.y = THREE.MathUtils.lerp(start.y, deskPos.y, u) + Math.sin(u * Math.PI) * 0.85;
        flyBag.rotation.y += dt * 4;
        flyBag.rotation.x += dt * 2;
      }
    }

    function animateOpen(dt) {
      openT += dt;
      if (flyBag.visible) {
        flyBag.position.lerp(deskPos, dt * 4);
        flyBag.scale.setScalar(1 + Math.min(0.35, openT * 0.4));
        // open lid tilt
        if (flyBag.children[1]) {
          flyBag.children[1].rotation.x = -Math.min(2.1, openT * 3.2);
        }
      }
      root.position.x = THREE.MathUtils.lerp(root.position.x, -0.55, dt * 1.5);
      camera.position.set(
        THREE.MathUtils.lerp(camera.position.x, 0.2, dt * 2),
        THREE.MathUtils.lerp(camera.position.y, 1.35, dt * 2),
        THREE.MathUtils.lerp(camera.position.z, 3.4, dt * 2)
      );
      camera.lookAt(deskPos.x, 1.1, 0);
      if (openT > 0.2) {
        glow.material.opacity = 0.18 + Math.sin(openT * 8) * 0.08;
      }
    }

    function tick() {
      if (!running) return;
      const dt = Math.min(0.033, clock.getDelta());

      if (state === "walk") animateWalk(dt);
      else if (state === "idle") {
        setPoseIdle();
        hips.position.y = 0.95 + Math.sin(clock.elapsedTime * 2) * 0.01;
      } else if (state === "throw") animateThrow(dt);
      else if (state === "open") animateOpen(dt);
      else if (state === "done") {
        root.visible = false;
        flyBag.visible = false;
        floor.visible = false;
        glow.visible = false;
      }

      renderer.render(scene, camera);
      requestAnimationFrame(tick);
    }
    setPoseIdle();
    tick();

    return {
      setState(next) {
        state = next;
        if (next === "walk") {
          root.visible = true;
          bag.visible = true;
          flyBag.visible = false;
        }
        if (next === "idle") setPoseIdle();
        if (next === "throw") {
          throwT = 0;
        }
        if (next === "open") {
          openT = 0;
          if (!flyBag.visible) {
            flyBag.visible = true;
            flyBag.position.copy(deskPos);
          }
        }
        if (next === "done") {
          running = false;
          root.visible = false;
          flyBag.visible = false;
        }
      },
      destroy() {
        running = false;
        renderer.dispose();
      },
      resize,
    };
  }

  window.EVHuman3D = { create: createHuman3D };
})();
