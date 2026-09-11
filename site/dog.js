// ZAPFISH everyday tasks — world 3: walking the dog.
// Right−left readout pulls the leash sideways; the gate is a firm pull (dog slows, obeys).
// Reward: dog on the path for 5 s. Aversive: dog in the pond, or dragged off the path after a squirrel.
export function Dog(ctx) {
  const { THREE, S, cam, G, pulse, flash, fishClone, mDark, COMMON_FOOT } = ctx;
  const HALF = 1.7; // path half-width
  const xc = z => 1.4 * Math.sin(z / 40) + 0.6 * Math.sin(z / 13);
  const st = { dogX: 0, dogZ: 0, dogV: 1.7, cartX: 0, cartZ: 2.4, steer: 0, firm: 0, onPath: 0, pathTime: 0, resisted: 0, splashes: 0, offs: 0, squirrel: null, nextSq: 5, wander: 0, reset: 0, chasing: false, leftPathDuringChase: false };
  const ponds = []; const trees = []; let dog, dogParts, cart, leash, fCart, fFish, fLeash, fDog, rider;

  function makeDog(scale = 1) {
    const g = new THREE.Group(); const fur = mDark(0xc79a5b, 0.85), dark = mDark(0x4a3423, 0.9);
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.3, 0.7), fur); body.position.y = 0.42; g.add(body);
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.24, 0.3), fur); head.position.set(0, 0.6, -0.48); g.add(head);
    const snout = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.12, 0.16), dark); snout.position.set(0, 0.54, -0.68); g.add(snout);
    for (const s of [-1, 1]) { const ear = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.16, 0.1), dark); ear.position.set(s * 0.14, 0.7, -0.42); ear.rotation.z = s * 0.4; g.add(ear); }
    const legs = [];
    for (const [x, z] of [[-0.12, -0.25], [0.12, -0.25], [-0.12, 0.25], [0.12, 0.25]]) { const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.04, 0.32, 8), fur); leg.position.set(x, 0.16, z); g.add(leg); legs.push(leg); }
    const tail = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.015, 0.3, 6), fur); tail.position.set(0, 0.55, 0.42); tail.rotation.x = -0.9; g.add(tail);
    g.traverse(m => { if (m.isMesh) m.castShadow = true; }); g.scale.setScalar(scale);
    return { g, legs, tail, head };
  }
  function makeCart() {
    const g = new THREE.Group(); const deck = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.08, 1.0), mDark(0x3a3f4b, 0.6)); deck.position.y = 0.3; g.add(deck);
    for (const [x, z] of [[-0.32, -0.35], [0.32, -0.35], [-0.32, 0.35], [0.32, 0.35]]) { const w = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.08, 14), mDark(0x0d0e12)); w.rotation.z = Math.PI / 2; w.position.set(x, 0.16, z); g.add(w); }
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.5, 8), mDark(0x8a93a3, 0.4)); post.position.set(0, 0.55, -0.45); g.add(post);
    g.traverse(m => { if (m.isMesh) m.castShadow = true; }); return g;
  }
  function makeLeash() { const m = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 1, 6), new THREE.MeshBasicMaterial({ color: 0xff5c8a })); return m; }
  function stretchLeash(mesh, a, b) { const d = new THREE.Vector3().subVectors(b, a); const len = d.length(); mesh.position.copy(a).addScaledVector(d, 0.5); mesh.scale.set(1, len, 1); mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize()); }
  function inPond(x, z) { return ponds.some(p => Math.hypot(x - p.x, z - p.z) < p.r - 0.3); }

  return {
    name: 'walking the dog', ctlTitle: 'Leash · firm pull', gain: 0.6,
    foot: '<b>Walking the dog.</b> A 4.8 km park loop. Right−left pulls the leash sideways, the gate is a firm pull that slows the dog; the leash is 2.8 m and pulls both ways when taut. Five seconds with the dog on the path is a reward; a squirrel dragging it off the path, or a dip in the pond, is aversive.' + COMMON_FOOT,
    build() {
      S.background = new THREE.Color(0xa9c4d8); S.fog = new THREE.Fog(0xa9c4d8, 40, 110);
      S.add(new THREE.HemisphereLight(0xe6efff, 0x4f6b46, 1.1)); const sun = new THREE.DirectionalLight(0xfff3e0, 2.0); sun.position.set(-18, 28, 12); sun.castShadow = true; sun.shadow.camera.left = -30; sun.shadow.camera.right = 30; sun.shadow.camera.top = 30; sun.shadow.camera.bottom = -30; sun.shadow.mapSize.set(1024, 1024); S.add(sun);
      const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 1200), mDark(0x4f8046, 1)); ground.rotation.x = -Math.PI / 2; ground.position.z = -400; ground.receiveShadow = true; S.add(ground);
      const N = 2000, step = 2.4; const path = new THREE.PlaneGeometry(1, 1, 1, N); const edgeL = path.clone(), edgeR = path.clone();
      const set = (geo, w0, w1) => { const p = geo.attributes.position; for (let i = 0; i <= N; i++) { const z = -i * step, c = xc(z); p.setXYZ(i * 2, c + w0, 0, z); p.setXYZ(i * 2 + 1, c + w1, 0, z); } p.needsUpdate = true; geo.computeVertexNormals(); geo.computeBoundingSphere(); };
      set(path, -HALF, HALF); set(edgeL, -HALF - 0.25, -HALF); set(edgeR, HALF, HALF + 0.25);
      for (const [geo, col, y] of [[path, 0xd9c9a0, 0.01], [edgeL, 0xf0e6c8, 0.02], [edgeR, 0xf0e6c8, 0.02]]) { const mat = mDark(col, 0.95); mat.side = THREE.DoubleSide; const m = new THREE.Mesh(geo, mat); m.position.y = y; m.receiveShadow = true; S.add(m); }
      let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
      for (let z = -40; z > -N * step; z -= 70 + rnd() * 40) { const side = rnd() < 0.5 ? -1 : 1; const r = 3.5 + rnd() * 2; const x = xc(z) + side * (HALF + r + 0.6); const pond = new THREE.Mesh(new THREE.CircleGeometry(r, 28), mDark(0x2f6bb0, 0.25)); pond.rotation.x = -Math.PI / 2; pond.position.set(x, 0.015, z); S.add(pond); ponds.push({ x, z, r }); }
      for (let z = 0; z > -N * step; z -= 9 + rnd() * 8) { const side = rnd() < 0.5 ? -1 : 1; const x = xc(z) + side * (HALF + 2.5 + rnd() * 9); if (inPond(x, z)) continue; const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 1.4, 7), mDark(0x5a4633, 0.9)); trunk.position.set(x, 0.7, z); const crown = new THREE.Mesh(new THREE.ConeGeometry(1.2 + rnd() * 0.8, 2.6 + rnd() * 1.4, 7), mDark(0x2f6b3a + Math.floor(rnd() * 0x001a00), 0.95)); crown.position.set(x, 2.6, z); trunk.castShadow = crown.castShadow = true; S.add(trunk); S.add(crown); trees.push({ x, z }); }
      for (let z = -15; z > -N * step; z -= 45) { const side = (Math.round(-z / 45) % 2) ? 1 : -1; const x = xc(z) + side * (HALF + 0.7); const post = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.07, 3.2, 8), mDark(0x2f3440, 0.6)); post.position.set(x, 1.6, z); post.castShadow = true; S.add(post); const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.18, 10, 8), mDark(0xf1ead6, 0.4)); lamp.position.set(x, 3.3, z); S.add(lamp); }
      for (let z = -5; z > -N * step; z -= 30 + rnd() * 25) { const side = rnd() < 0.5 ? -1 : 1; const x = xc(z) + side * (HALF + 1.4); const bench = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.08, 0.45), mDark(0x8a6a3f, 0.8)); bench.position.set(x, 0.45, z); bench.castShadow = true; S.add(bench); for (const dx of [-0.6, 0.6]) { const leg = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.45, 0.4), mDark(0x2f3440)); leg.position.set(x + dx, 0.22, z); S.add(leg); } }
      const d = makeDog(); dog = d.g; dogParts = d; S.add(dog);
      cart = makeCart(); S.add(cart); rider = fishClone(1.0); rider.children[0].position.y += 0.62; rider.children[0].rotation.y = -Math.PI / 2; S.add(rider);
      leash = makeLeash(); S.add(leash);
      st.sqMesh = new THREE.Group(); const sb = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.14, 0.3), mDark(0xd9d0c0, 0.8)); sb.position.y = 0.1; st.sqMesh.add(sb); const stail = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.26, 0.08), mDark(0xd9d0c0, 0.8)); stail.position.set(0, 0.24, 0.16); st.sqMesh.add(stail); st.sqMesh.visible = false; S.add(st.sqMesh);
    },
    buildFish(FS) {
      const H = -0.95; fCart = makeCart(); fCart.scale.setScalar(1.3); fCart.position.set(-0.5, -0.55, 0.3); fCart.rotation.y = H; FS.add(fCart);
      fFish = fishClone(1.3); fFish.children[0].position.y += 0.8; fFish.children[0].rotation.y = -Math.PI / 2; fFish.position.copy(fCart.position); fFish.rotation.y = H; FS.add(fFish);
      const d = makeDog(0.9); fDog = d.g; fDog.position.set(-0.5 - Math.sin(H) * 2.6, -0.55, 0.3 - Math.cos(H) * 2.6); fDog.rotation.y = H; FS.add(fDog); st.fDogParts = d; st.fH = H;
      fLeash = makeLeash(); FS.add(fLeash);
      return { cam: [2.6, 1.0, 3.4], look: [0.5, 0.15, -0.5] };
    },
    spawnSquirrel() { const side = Math.random() < 0.5 ? -1 : 1; const z = st.dogZ - 7; st.squirrel = { x: xc(z) + side * 5.5, z, dir: -side, t: 0, life: 4.5 }; st.chasing = true; st.leftPathDuringChase = false; flash('SQUIRREL', 0.8); st.sqMesh.visible = true; },
    step(dt) {
      if (st.reset > 0) { st.reset -= dt; if (st.reset <= 0) { st.dogX = xc(st.dogZ); st.cartX = st.dogX; st.cartZ = st.dogZ + 2.4; } }
      else {
        // squirrel
        st.nextSq -= dt; if (!st.squirrel && st.nextSq <= 0) { this.spawnSquirrel(); st.nextSq = 7 + Math.random() * 6; }
        if (st.squirrel) { const q = st.squirrel; q.t += dt; q.x += q.dir * 2.2 * dt; q.z -= 0.4 * dt; st.sqMesh.position.set(q.x, 0, q.z); st.sqMesh.rotation.y = q.dir > 0 ? -Math.PI / 2 : Math.PI / 2; if (q.t > q.life) { st.squirrel = null; st.sqMesh.visible = false; st.chasing = false; if (!st.leftPathDuringChase) { st.resisted++; flash('RESISTED'); } } }
        // dog lateral dynamics: wander + squirrel pull + leash pull toward (cart + steer)
        st.wander += (Math.random() - 0.5) * 2.5 * dt; st.wander = Math.max(-1, Math.min(1, st.wander * 0.98));
        let lat = st.wander * 0.9;
        if (st.squirrel) lat += Math.sign(st.squirrel.x - st.dogX) * (st.firm > 0 ? 0.9 : 2.4);
        const anchor = st.cartX + st.steer; lat += (anchor - st.dogX) * (st.firm > 0 ? 3.2 : 1.1);
        st.dogV = st.firm > 0 ? 0.7 : 1.7;
        st.dogX += Math.max(-2.6, Math.min(2.6, lat)) * dt; st.dogZ -= st.dogV * dt;
        // cart follows the dog with lag; the leash has a real length (2.8 m): when taut it pulls both ways
        st.cartZ += ((st.dogZ + 2.4) - st.cartZ) * Math.min(1, dt * 2.5); st.cartX += ((st.dogX) - st.cartX) * Math.min(1, dt * 1.2);
        const ddx = st.dogX - st.cartX, ddz = st.dogZ - st.cartZ, dlen = Math.hypot(ddx, ddz); st.taut = dlen > 2.8;
        if (st.taut) { const over = (dlen - 2.8) / dlen; st.dogX -= ddx * over * 0.6; st.dogZ -= ddz * over * 0.6; st.cartX += ddx * over * 0.4; st.cartZ += ddz * over * 0.4; }
        if (st.firm > 0) st.firm -= dt;
        const off = st.dogX - xc(st.dogZ); const on = Math.abs(off) < HALF + 0.2;
        if (inPond(st.dogX, st.dogZ)) { st.splashes++; st.reset = 1.0; pulse('aversive'); flash('SPLASH'); st.onPath = 0; st.squirrel = null; st.sqMesh.visible = false; st.chasing = false; }
        else if (Math.abs(off) > HALF + 2.5) { st.offs++; st.reset = 0.8; pulse('aversive'); flash('OFF THE PATH'); st.onPath = 0; st.leftPathDuringChase = true; }
        else { if (!on && st.chasing) st.leftPathDuringChase = true; if (on) { st.onPath += dt; st.pathTime += dt; if (st.onPath >= 5) { st.onPath = 0; pulse('reward'); flash('GOOD DOG'); } } else st.onPath = 0; }
      }
      // place
      const heading = Math.atan2(-(st.dogX - st.cartX), (st.cartZ - st.dogZ)); dog.position.set(st.dogX, 0, st.dogZ); dog.rotation.y = heading;
      const gait = st.dogV * 9; for (let i = 0; i < 4; i++) dogParts.legs[i].rotation.x = Math.sin(G.elapsed * gait + i * Math.PI / 2) * 0.5; dogParts.tail.rotation.z = Math.sin(G.elapsed * 6) * 0.4; dogParts.head.rotation.y = st.squirrel ? Math.sign(st.squirrel.x - st.dogX) * 0.6 : 0;
      cart.position.set(st.cartX, 0, st.cartZ); cart.rotation.y = heading; rider.position.copy(cart.position); rider.rotation.y = heading; rider.position.y = Math.sin(G.elapsed * 5) * 0.015;
      stretchLeash(leash, new THREE.Vector3(st.cartX, 0.72, st.cartZ - 0.45), new THREE.Vector3(st.dogX, 0.6, st.dogZ + 0.25)); leash.material.color.setHex(st.taut ? 0xffffff : 0xff5c8a);
      const back = new THREE.Vector3(0, 4.2, 6.2); cam.position.lerp(new THREE.Vector3(st.cartX, 0, st.cartZ).add(back), Math.min(1, dt * 5)); cam.lookAt(st.dogX, 0.4, st.dogZ - 2.5);
      if (fCart) { const H = st.fH; fCart.rotation.x = st.firm > 0 ? -0.12 : 0; fFish.rotation.x = fCart.rotation.x; fFish.rotation.y = H + st.steer * 0.35; const side = st.steer * 1.0 + (st.squirrel ? Math.sign(st.squirrel.x - st.dogX) * 0.6 : 0); fDog.position.set(-0.5 - Math.sin(H) * 2.6 + Math.cos(H) * side, -0.55, 0.3 - Math.cos(H) * 2.6 - Math.sin(H) * side); const fp = st.fDogParts; for (let i = 0; i < 4; i++) fp.legs[i].rotation.x = Math.sin(G.elapsed * gait + i * Math.PI / 2) * 0.5; fp.tail.rotation.z = Math.sin(G.elapsed * 6) * 0.4; const post = new THREE.Vector3(-0.5 - Math.sin(H) * 0.6, 0.25, 0.3 - Math.cos(H) * 0.6); stretchLeash(fLeash, post, new THREE.Vector3(fDog.position.x, 0.0, fDog.position.z)); }
    },
    act(ctl, gateRise, gateOpen) { st.steer = Math.max(-2.2, Math.min(2.2, ctl * this.gain)); if (gateRise) { st.firm = 0.9; flash('FIRM PULL', 0.4); } },
    mode() { return (st.squirrel ? 'squirrel!' : 'easy') + ' | walking the dog'; },
    speed() { return (st.dogV * 3.6).toFixed(1) + ' km/h'; },
    score() { return `on path <b>${st.pathTime >= 60 ? Math.floor(st.pathTime / 60) + 'm ' + Math.floor(st.pathTime % 60) + 's' : st.pathTime.toFixed(0) + ' s'}</b> · walked <b>${(-st.dogZ / 1000).toFixed(2)} km</b><br>resisted <b>${st.resisted}</b> · splashes <b>${st.splashes}</b> · off path <b>${st.offs}</b> · leash <b>${st.taut ? 'TAUT' : 'slack'}</b>`; },
  };
}
