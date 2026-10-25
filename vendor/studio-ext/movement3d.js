/* The `movement3d` element: a mechanical watch movement drawn in code with three.js (vendor/three, MIT), running.
   video-director, ours. A simplified principle, not any maker's engineering drawing.

     {type: 'movement3d', explode_at: 2.4, labels: true, spin: 8, parts: [...ids to label], note: '...'}

   The train is the real chain: the barrel's mainspring turns the centre wheel, then the third and fourth (seconds)
   wheels, the escape wheel and the pallet fork, which the balance wheel and its hairspring let go one beat at a time.
   Each wheel drives the next one's pinion, so every speed follows from the ratios; the fourth wheel turns once a
   minute. Everything is set from the scene time alone (no clock, no randomness), so every frame renders the same.
   `explode_at` lifts the parts apart in layers with their names; the camera turns to show the layers. */
import * as THREE from 'three';
import { RoomEnvironment } from '../three/examples/jsm/environments/RoomEnvironment.js';

const PM = window.PM;
const TAU = Math.PI * 2;
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);

// the train (millimetre-like units). R: wheel radius, p: pinion radius, n: teeth. Each wheel meshes the next pinion.
const TRAIN = [
  { id: 'barrel', x: -4.5, y: 4.4, R: 5.4, n: 72, p: 0, z: 1.0, layer: 1, name: 'البرميل والنابض الرئيسي', tone: 'gold' },
  { id: 'center', x: 0.0, y: 0.0, R: 4.4, n: 64, p: 0.9, z: 2.0, layer: 2, name: 'عجلة الوسط', tone: 'gold' },
  { id: 'third', x: 3.9, y: -3.45, R: 3.8, n: 60, p: 0.8, z: 2.6, layer: 3, name: 'العجلة الثالثة', tone: 'gold' },
  { id: 'fourth', x: 8.2, y: -2.2, R: 3.3, n: 60, p: 0.7, z: 3.2, layer: 4, name: 'عجلة الثواني', tone: 'gold' },
  { id: 'escape', x: 9.2, y: -6.0, R: 2.4, n: 15, p: 0.6, z: 3.8, layer: 5, name: 'عجلة الانفلات', tone: 'steel', club: true },
];
const FORK = { id: 'fork', x: 6.0, y: -8.4, z: 4.2, layer: 6, name: 'الشوكة' };
const BAL = { id: 'balance', x: 3.0, y: -9.9, R: 4.0, z: 5.2, layer: 7, name: 'عجلة التوازن' };
const SPRING = { id: 'hairspring', name: 'النابض الشعري', layer: 8 };
const PLATE = { id: 'plate', name: 'اللوحة الرئيسية', layer: 0 };
const BEATS = 2.75;                  // beats per second, so that the fourth wheel turns once a minute (simplified)

function gearShape(R, n, club) {
  const s = new THREE.Shape(), root = R * (club ? 0.78 : 0.9), steps = n * 4;
  for (let i = 0; i <= steps; i++) {
    const a = (i / steps) * TAU, q = i % 4;
    let r = q === 1 || q === 2 ? R : root;
    if (club && q === 2) r = R * 0.93;
    const x = Math.cos(a) * r, y = Math.sin(a) * r;
    i ? s.lineTo(x, y) : s.moveTo(x, y);
  }
  if (R > 1.8) {                                         // crossings: five spokes cut into the wheel, like a real one
    const hole = (a0, a1, r0, r1) => {
      const h = new THREE.Path(); h.absarc(0, 0, r1, a0, a1, false); h.absarc(0, 0, r0, a1, a0, true); h.closePath(); return h;
    };
    const k = club ? 4 : 5, gap = 0.28;
    for (let i = 0; i < k; i++) s.holes.push(hole((i / k) * TAU + gap, ((i + 1) / k) * TAU - gap, R * 0.28, root * 0.82));
  }
  return s;
}

PM.builders.movement3d = function (spec, ctx) {
  const W = ctx.S.width, H = ctx.S.height, dpr = window.devicePixelRatio || 1;
  if (spec.x == null) spec.x = 0;
  if (spec.y == null) spec.y = 0;
  const wrap = document.createElement('div');
  wrap.style.cssText = `position:relative;width:${W}px;height:${H}px`;
  const gl = document.createElement('canvas'), ov = document.createElement('canvas');
  for (const c of [gl, ov]) { c.width = Math.round(W * dpr); c.height = Math.round(H * dpr); c.style.cssText = `position:absolute;left:0;top:0;width:${W}px;height:${H}px`; wrap.appendChild(c); }

  const renderer = new THREE.WebGLRenderer({ canvas: gl, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(gl.width, gl.height, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 0.9;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;
  const key = new THREE.DirectionalLight(0xfff4e0, 2.2); key.position.set(-12, 18, 26); scene.add(key);
  const rim = new THREE.DirectionalLight(0xbcd2ff, 1.4); rim.position.set(16, -6, -10); scene.add(rim);
  scene.add(new THREE.AmbientLight(0xffffff, 0.25));
  const cam = new THREE.PerspectiveCamera(30, W / H, 0.1, 400);

  const M = {
    gold: new THREE.MeshPhysicalMaterial({ color: 0xd8b469, metalness: 1, roughness: 0.28, clearcoat: 0.3 }),
    steel: new THREE.MeshPhysicalMaterial({ color: 0xd6dbe3, metalness: 1, roughness: 0.18 }),
    plate: new THREE.MeshPhysicalMaterial({ color: 0x7d838c, metalness: 1, roughness: 0.5 }),
    bridge: new THREE.MeshPhysicalMaterial({ color: 0xa9aeb6, metalness: 1, roughness: 0.32 }),
    ruby: new THREE.MeshPhysicalMaterial({ color: 0xa3122c, metalness: 0, roughness: 0.08, transmission: 0.2, clearcoat: 1, emissive: 0x2a0008 }),
    blue: new THREE.MeshPhysicalMaterial({ color: 0x2a4fa0, metalness: 1, roughness: 0.3 }),
  };
  const root = new THREE.Group(); scene.add(root);
  const parts = {};                                       // id -> {obj, base z, layer, name, anchor}
  const add = (id, obj, z, layer, name) => { obj.position.z = z; root.add(obj); parts[id] = { obj, z, layer, name }; return obj; };

  // the main plate, with a jewel at every pivot
  const plateShape = new THREE.Shape(); plateShape.absarc(2, -3, 15.2, 0, TAU, false);
  const plate = new THREE.Mesh(new THREE.ExtrudeGeometry(plateShape, { depth: 0.8, bevelEnabled: true, bevelSize: 0.25, bevelThickness: 0.2, curveSegments: 96 }), M.plate);
  add('plate', plate, -0.8, 0, PLATE.name);
  const jewel = (x, y, z, parent) => { const j = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.25, 24), M.ruby); j.rotation.x = Math.PI / 2; j.position.set(x, y, z); (parent || root).add(j); return j; };

  // the train: each wheel with its pinion and arbor
  TRAIN.forEach((w) => {
    const g = new THREE.Group(); g.position.set(w.x, w.y, 0);
    const wheel = new THREE.Mesh(new THREE.ExtrudeGeometry(gearShape(w.R, w.n, w.club), { depth: 0.22, bevelEnabled: false, curveSegments: 4 }), M[w.tone]);
    g.add(wheel);
    if (w.p) { const pin = new THREE.Mesh(new THREE.ExtrudeGeometry(gearShape(w.p, 8, false), { depth: 0.9, bevelEnabled: false }), M.steel); pin.position.z = -0.95; g.add(pin); }
    const arbor = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 2.4, 16), M.steel); arbor.rotation.x = Math.PI / 2; g.add(arbor);
    if (w.id === 'barrel') {                              // the drum and the mainspring coiled inside it
      const drum = new THREE.Mesh(new THREE.CylinderGeometry(w.R * 0.86, w.R * 0.86, 0.9, 64, 1, true), M.gold); drum.rotation.x = Math.PI / 2; drum.position.z = 0.55; g.add(drum);
      const pts = []; for (let i = 0; i <= 600; i++) { const a = i / 600 * TAU * 7, r = 0.9 + (w.R * 0.78 - 0.9) * (i / 600); pts.push(new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, 0.5)); }
      g.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 900, 0.07, 6, false), M.blue));
    }
    jewel(0, 0, 1.3, g);
    w.obj = add(w.id, g, w.z, w.layer, w.name);
  });

  // the pallet fork: a lever with two ruby pallet stones
  const fork = new THREE.Group(); fork.position.set(FORK.x, FORK.y, 0);
  const lever = new THREE.Shape(); lever.moveTo(-0.25, 0); lever.lineTo(-0.25, 3.2); lever.lineTo(0.25, 3.2); lever.lineTo(0.25, 0); lever.closePath();
  const toE = Math.atan2(TRAIN[4].y - FORK.y, TRAIN[4].x - FORK.x) - Math.PI / 2, toB = Math.atan2(BAL.y - FORK.y, BAL.x - FORK.x) - Math.PI / 2;
  for (const [ang, len] of [[toE + 0.42, 2.4], [toE - 0.42, 2.4], [toB, 2.6]]) {
    const arm = new THREE.Mesh(new THREE.ExtrudeGeometry(lever, { depth: 0.2, bevelEnabled: false }), M.steel); arm.rotation.z = ang; arm.scale.y = len / 3.2; fork.add(arm);
    if (len === 2.4) { const st = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.6, 0.3), M.ruby); st.position.set(-Math.sin(ang) * 2.3, Math.cos(ang) * 2.3, 0.1); st.rotation.z = ang; fork.add(st); }
  }
  jewel(0, 0, 0.35, fork);
  add('fork', fork, FORK.z, FORK.layer, FORK.name);

  // the balance wheel and its hairspring, under the balance cock
  const bal = new THREE.Group(); bal.position.set(BAL.x, BAL.y, 0);
  const rimRing = new THREE.Mesh(new THREE.TorusGeometry(BAL.R, 0.32, 16, 96), M.gold); bal.add(rimRing);
  for (let i = 0; i < 3; i++) { const sp = new THREE.Mesh(new THREE.BoxGeometry(0.28, BAL.R * 2, 0.18), M.gold); sp.rotation.z = (i / 3) * Math.PI; bal.add(sp); }
  for (let i = 0; i < 12; i++) { const s = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.5, 10), M.gold); const a = i / 12 * TAU; s.position.set(Math.cos(a) * (BAL.R + 0.32), Math.sin(a) * (BAL.R + 0.32), 0); s.rotation.z = a + Math.PI / 2; bal.add(s); }
  jewel(0, 0, 0.3, bal);
  add('balance', bal, BAL.z, BAL.layer, BAL.name);
  const springGroup = new THREE.Group(); springGroup.position.set(BAL.x, BAL.y, 0);
  const spiral = (k) => { const pts = []; for (let i = 0; i <= 500; i++) { const a = i / 500 * TAU * 11, r = (0.5 + 2.6 * (i / 500)) * k; pts.push(new THREE.Vector3(Math.cos(a) * r, Math.sin(a) * r, 0)); } return pts; };
  const springMesh = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(spiral(1)), 700, 0.045, 5, false), M.blue);
  springGroup.add(springMesh);
  add('hairspring', springGroup, BAL.z + 0.6, SPRING.layer, SPRING.name);
  const cock = new THREE.Shape(); cock.moveTo(0, -0.75); cock.lineTo(6.5, -0.5); cock.lineTo(6.5, 0.5); cock.lineTo(0, 0.75); cock.absarc(0, 0, 0.75, Math.PI / 2, -Math.PI / 2, false);
  const cockMesh = new THREE.Mesh(new THREE.ExtrudeGeometry(cock, { depth: 0.45, bevelEnabled: true, bevelSize: 0.12, bevelThickness: 0.1 }), M.plate);
  cockMesh.position.set(BAL.x, BAL.y, 0); cockMesh.rotation.z = -2.3; cockMesh.material = M.bridge;
  add('cock', cockMesh, BAL.z + 1.4, 9, 'جسر عجلة التوازن');

  // label drawing on the overlay canvas, in the page's Arabic face
  const X = ov.getContext('2d');
  const labelled = spec.parts || ['barrel', 'center', 'fourth', 'escape', 'fork', 'balance', 'hairspring'];
  const screen = (v) => { const p = v.clone().project(cam); return [(p.x * 0.5 + 0.5) * W, (-p.y * 0.5 + 0.5) * H]; };
  const at = spec.explode_at, dur = spec.explode_dur || 1.4, gap = spec.gap || 2.6, spin = spec.spin == null ? 8 : spec.spin;
  const tips = { barrel: [TRAIN[0].x, TRAIN[0].y], center: [0, 0], third: [TRAIN[2].x, TRAIN[2].y], fourth: [TRAIN[3].x, TRAIN[3].y],
                 escape: [TRAIN[4].x, TRAIN[4].y], fork: [FORK.x, FORK.y], balance: [BAL.x - BAL.R * 0.7, BAL.y], hairspring: [BAL.x + 1.6, BAL.y + 1.6], plate: [-9, -9] };

  return {
    node: wrap, w: W, h: H, anchor: 'tl',
    update(lt) {
      const t = Math.max(0, lt);
      // the escapement: a beat every 1/BEATS s, the escape wheel jumps half a tooth at the start of each beat
      const beat = t * BEATS, nb = Math.floor(beat), fb = beat - nb;
      const escAng = -(TAU / TRAIN[4].n / 2) * (nb + ease(clamp(fb / 0.18)));
      let w = escAng;
      for (let i = 4; i >= 0; i--) {                     // back up the train: each wheel turns its pinion's ratio slower
        const g = TRAIN[i];
        g.obj.rotation.z = w;
        if (i > 0) w = -w * (g.p / TRAIN[i - 1].R);
      }
      const swing = Math.sin(Math.PI * beat);            // the balance swings once every two beats
      bal.rotation.z = 3.4 * swing;
      const breathe = 1 + 0.07 * swing;
      springMesh.scale.set(breathe, breathe, 1); springMesh.rotation.z = 1.2 * swing;
      fork.rotation.z = 0.12 * Math.tanh(5 * Math.cos(Math.PI * beat));

      // exploded view: every part lifts to its layer; the camera turns to see the layers from the side
      const k = at == null ? 0 : ease(clamp((lt - at) / dur));
      for (const id in parts) { const p = parts[id]; p.obj.position.z = p.z + k * p.layer * gap; }
      const az = (-20 + spin * t) * Math.PI / 180, el = (58 - 24 * k) * Math.PI / 180, dist = (spec.dist || 104) + 30 * k;
      const c = new THREE.Vector3(2.5, -3, 3 + k * 11);
      cam.position.set(c.x + dist * Math.cos(el) * Math.sin(az), c.y - dist * Math.cos(el) * Math.cos(az), c.z + dist * Math.sin(el));
      cam.up.set(0, 0, 1); cam.lookAt(c);
      renderer.render(scene, cam);

      // the names, once the parts have separated
      X.setTransform(dpr, 0, 0, dpr, 0, 0); X.clearRect(0, 0, W, H);
      const lk = at == null ? 0 : clamp((lt - at - dur * 0.6) / 0.6);
      if (spec.labels !== false && lk > 0) {
        const pts = labelled.filter((id) => parts[id]).map((id) => {
          const [x, y] = tips[id], v = new THREE.Vector3(x, y, parts[id].obj.position.z + 0.3);
          const [sx, sy] = screen(v); return { id, sx, sy, name: parts[id].name };
        }).sort((a, b) => a.sy - b.sy);
        X.font = '700 21px Cairo'; X.textBaseline = 'middle'; X.globalAlpha = lk;
        const used = { l: [], r: [] };
        pts.forEach((p) => {
          const side = p.sx < W / 2 ? 'l' : 'r';
          let ly = Math.max(400, Math.min(960, p.sy));
          for (const u of used[side]) if (Math.abs(u - ly) < 38) ly = u + 38;
          used[side].push(ly);
          const tw = X.measureText(p.name).width, bx = side === 'l' ? 34 : W - 34 - tw - 24;
          X.strokeStyle = 'rgba(243,240,232,.75)'; X.lineWidth = 1.5;
          X.beginPath(); X.moveTo(p.sx, p.sy); X.lineTo(side === 'l' ? bx + tw + 24 : bx, ly); X.stroke();
          X.fillStyle = '#C9A35F'; X.beginPath(); X.arc(p.sx, p.sy, 4, 0, TAU); X.fill();
          X.fillStyle = 'rgba(10,11,14,.82)'; X.beginPath(); X.roundRect(bx, ly - 17, tw + 24, 34, 8); X.fill();
          X.fillStyle = '#F3F0E8'; X.direction = 'rtl'; X.textAlign = 'right'; X.fillText(p.name, bx + tw + 12, ly + 1);
        });
        X.globalAlpha = 1;
      }
    },
  };
};
