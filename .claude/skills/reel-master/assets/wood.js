// The Wood Marquetry veneer engine (Time Keeper's own style). Fine-scene defaults: const FINE = { scale: 0.45, seam: 0.7, seamA: 0.32 }
// spread into every piece() call. Used only when the style package on the owner's Mac cannot be reached.
export function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const h2 = (x, y, s) => { const n = Math.sin(x * 127.1 + y * 311.7 + s * 74.7) * 43758.5453; return n - Math.floor(n); };
function vn(x, y, s) { const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi, u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = h2(xi, yi, s), b = h2(xi + 1, yi, s), c = h2(xi, yi + 1, s), d = h2(xi + 1, yi + 1, s); return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v; }
const fbm = (x, y, s, o = 4) => { let f = 0, a = 0.5, k = 1; for (let i = 0; i < o; i++) { f += a * vn(x * k, y * k, s + i * 13); a *= 0.5; k *= 2.03; } return f; };
const GRAIN = {};
export function grain(kind = 'straight', seed = 1, S = 512) {
  const key = kind + seed; if (GRAIN[key]) return GRAIN[key];
  const c = document.createElement('canvas'); c.width = c.height = S; const g = c.getContext('2d');
  const im = g.createImageData(S, S), D = im.data;
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
    const X = x / S, Y = y / S; let u;
    const warp = fbm(X * 0.9, Y * 2.2, seed) * 3.2 + fbm(X * 3.5, Y * 6, seed + 2) * 0.6;
    if (kind === 'flat') { const w = fbm(X * 1.6, Y * 1.1, seed) * 0.4; u = (Math.abs(Y - 0.5 + w * 0.5) * 2 + (X * 0.3 - 0.15) ** 2 * 1.4) * 22 + warp * 0.5; }
    else if (kind === 'wavy') { u = Y * 46 + warp; } else { u = Y * 58 + warp; }
    u += fbm(0.3, Y * 30, seed + 7) * 2.5;
    const ring = u - Math.floor(u), late = Math.pow(Math.max(0, Math.sin(ring * Math.PI)), 10), soft = Math.sin(ring * Math.PI * 2) * 0.5;
    const pores = (vn(X * 700, Y * 220, seed + 9) - 0.5), fleck = Math.max(0, vn(X * 160, Y * 260, seed + 11) - 0.72) * 2.2, fig = fbm(X * 2.5, Y * 1.2, seed + 3) - 0.5;
    let v = 0.5 - late * 0.16 + soft * 0.035 + pores * 0.09 - fleck * 0.12 + fig * 0.16;
    if (kind === 'wavy') v += Math.sin(X * 90 + fbm(X * 2, Y * 2, seed) * 6) * 0.035;
    v = Math.max(0, Math.min(1, v)) * 255; const i = (y * S + x) * 4; D[i] = D[i + 1] = D[i + 2] = v; D[i + 3] = 255;
  }
  g.putImageData(im, 0, 0); GRAIN[key] = c; return c;
}
export const WOOD = {
  holly: '#efe6cf', sycamore: '#e6d6b0', maple: '#dcc496', ash: '#d2b886', lime: '#e2cf9e',
  oak: '#c09a62', pear: '#c9906a', cherry: '#b46d45', padauk: '#c0562e', mahogany: '#8e4a2c',
  teak: '#9a6a38', walnut: '#6a4630', rosewood: '#4e2f22', ebony: '#2c211b', wenge: '#3c2c22',
  ink: '#1f3d5c', navy: '#27507a', blue: '#3a6f98', sky: '#6d9fbe', pale: '#a9c7d4',
  teal: '#1f6f78', turq: '#3c9a9a', aqua: '#7fbdb5', mint: '#b9d8c9',
  gold: '#e3a94a', amber: '#d98b3c', orange: '#cf6b33', coral: '#d9875f', rose: '#c98a7a', peach: '#e7b98e',
};
const hex = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
export const tone = (h, k) => { const c = hex(WOOD[h] || h); const t = k < 0 ? mix(c, [30, 18, 10], -k) : mix(c, [255, 248, 230], k); return `rgb(${t})`; };
// poly [[x,y]…]; o: { wood (name|hex), k (+lighter/−darker), angle (grain rad), kind ('straight'|'flat'|'wavy'), seed, scale, seam, seamA, grainA }
export function piece(ctx, poly, o = {}) {
  if (poly.length < 3) return; const r = rng((o.seed ?? 1) * 9301 + 7);
  const path = new Path2D(); poly.forEach(([x, y], i) => i ? path.lineTo(x, y) : path.moveTo(x, y)); path.closePath();
  let cx = 0, cy = 0; for (const [x, y] of poly) { cx += x; cy += y; } cx /= poly.length; cy /= poly.length;
  ctx.save(); ctx.clip(path);
  ctx.fillStyle = tone(o.wood ?? 'maple', (o.k ?? 0) + (r() - 0.5) * 0.08); ctx.fill(path);
  const G = grain(o.kind ?? 'straight', o.gseed ?? (1 + Math.floor(r() * 8)));
  const ang = (o.angle ?? 0) + (r() - 0.5) * 0.05, sc = o.scale ?? 0.8;
  ctx.translate(cx, cy); ctx.rotate(ang); ctx.scale(sc, sc);
  let rad = 0; for (const [x, y] of poly) rad = Math.max(rad, Math.hypot(x - cx, y - cy)); rad = rad / sc + 4;
  const ox = -r() * G.width, oy = -r() * G.height, Sz = G.width, tiles = [];
  for (let ty = Math.floor((-rad - oy) / Sz) - 1; ty * Sz + oy < rad; ty++) for (let tx = Math.floor((-rad - ox) / Sz) - 1; tx * Sz + ox < rad; tx++) tiles.push([ox + tx * Sz, oy + ty * Sz]);
  ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = o.grainA ?? 0.75; for (const [x, y] of tiles) ctx.drawImage(G, x, y);
  ctx.globalCompositeOperation = 'multiply'; ctx.globalAlpha = 0.16; for (const [x, y] of tiles) ctx.drawImage(G, x, y);
  ctx.restore();
  ctx.save(); ctx.lineJoin = 'round'; ctx.strokeStyle = `rgba(46,28,14,${o.seamA ?? 0.55})`; ctx.lineWidth = o.seam ?? 1.1; ctx.stroke(path); ctx.restore();
}
// a strip between y=top(x) and y=bot(x) cut into leaves with shared slanted joints
export function band(x0, x1, top, bot, { seed = 1, minW = 70, maxW = 220, slant = 0.25, step = 8 } = {}) {
  const r = rng(seed), J = [{ x: x0, s: 0 }]; let a = x0;
  while (a < x1 - 1) { let b = Math.min(x1, a + minW + r() * (maxW - minW)); if (x1 - b < minW * 0.6) b = x1; J.push({ x: b, s: b >= x1 ? 0 : (r() - 0.5) * slant * 60 }); a = b; }
  const out = [];
  for (let i = 0; i + 1 < J.length; i++) { const L = J[i], Rr = J[i + 1], la = L.x + L.s / 2, ra = Rr.x + Rr.s / 2, lb = L.x - L.s / 2, rb = Rr.x - Rr.s / 2, T = [], B = [];
    const n = Math.max(2, Math.ceil((ra - la) / step)); for (let k = 0; k <= n; k++) { const x = la + (ra - la) * k / n; T.push([x, top(x)]); }
    const m = Math.max(2, Math.ceil((rb - lb) / step)); for (let k = m; k >= 0; k--) { const x = lb + (rb - lb) * k / m; B.push([x, bot(x)]); }
    out.push([...T, ...B]); }
  return out;
}
export const circle = (cx, cy, r, n = 64) => Array.from({ length: n }, (_, i) => [cx + Math.cos(i / n * Math.PI * 2) * r, cy + Math.sin(i / n * Math.PI * 2) * r]);
export function slabY(poly, y0, y1) { return clipLine(clipLine(poly, p => p[1] >= y0, y0, 1), p => p[1] <= y1, y1, 1); }
export function slabX(poly, x0, x1) { return clipLine(clipLine(poly, p => p[0] >= x0, x0, 0), p => p[0] <= x1, x1, 0); }
function clipLine(poly, inside, v, ax) { const out = []; for (let i = 0; i < poly.length; i++) { const a = poly[i], b = poly[(i + 1) % poly.length], ia = inside(a), ib = inside(b);
  if (ia) out.push(a); if (ia !== ib) { const t = (v - a[ax]) / (b[ax] - a[ax]); out.push([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]); } } return out; }
export function split(poly, px, py, a) { const nx = -Math.sin(a), ny = Math.cos(a), side = p => (p[0] - px) * nx + (p[1] - py) * ny, L = [], R = [];
  for (let i = 0; i < poly.length; i++) { const p = poly[i], q = poly[(i + 1) % poly.length], sp = side(p), sq = side(q); (sp >= 0 ? L : R).push(p);
    if ((sp >= 0) !== (sq >= 0)) { const t = sp / (sp - sq), m = [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]; L.push(m); R.push(m); } } return [L, R]; }
export function varnish(ctx, x0, y0, x1, y1) { ctx.save(); const g = ctx.createLinearGradient(x0, y0, x1, y1);
  g.addColorStop(0, 'rgba(255,245,225,0.10)'); g.addColorStop(0.35, 'rgba(255,245,225,0.0)'); g.addColorStop(0.62, 'rgba(255,240,215,0.06)'); g.addColorStop(1, 'rgba(0,0,0,0.06)');
  ctx.fillStyle = g; ctx.fillRect(x0, y0, x1 - x0, y1 - y0); ctx.restore(); }
