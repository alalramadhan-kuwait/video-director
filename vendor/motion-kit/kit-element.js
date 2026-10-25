/* The `kit` element: video-ad-editor's motion kit (motion-kit.js, MIT, see PROVENANCE.md) drawn inside a paper-story
   scene. Ours, not upstream.

     {type: 'kit', draw: [{fn: 'odometer', s: 0.6, dur: 1.6, val: 1950, cx: 540, cy: 820, size: 190}, ...],
      colors: {bg, ink, acc, clay, mut}, font: 'Cairo'}

   The element is a full-frame canvas in the kit's own design pixels (1080x1920, whatever the storyboard size); each
   `draw` entry calls MK[fn](t, entry) with t in seconds from the scene start, so `s` and `e` are scene times.
   Every frame is drawn from t alone (the kit is pure in t), so stills, resumed renders and parallel pages agree.
   The kit reads its canvas and palette from globals (X, BG, INK, ACC, CLAY, MUT, FONT); they are set for each draw
   and put back after it. */
(function () {
  const PM = window.PM, G = window, KW = 1080, KH = 1920;
  const GLOBALS = ['X', 'BG', 'INK', 'ACC', 'CLAY', 'MUT', 'FONT'];
  if (document.fonts) ['700', '800'].forEach((w) => document.fonts.load(w + ' 40px Cairo'));

  PM.builders.kit = function (spec, ctx) {
    if (!G.MK) throw new Error('motion kit: motion-kit.js is not loaded');
    (spec.draw || []).forEach((d) => { if (typeof G.MK[d.fn] !== 'function') throw new Error('motion kit: no component "' + d.fn + '"'); });
    if (spec.x == null) spec.x = 0;                 // the canvas covers the frame from its top-left corner
    if (spec.y == null) spec.y = 0;
    const W = ctx.S.width, H = ctx.S.height, th = ctx.theme || {};
    const cv = document.createElement('canvas');
    cv.width = KW; cv.height = KH;
    cv.style.width = W + 'px'; cv.style.height = H + 'px'; cv.style.display = 'block';
    const X = cv.getContext('2d');
    const c = Object.assign({ bg: th.bg || '#E4DFD3', ink: '#111111', acc: '#C9A35F', clay: '#8A6A3A', mut: '#6E6A62' }, spec.colors || {});
    return {
      node: cv, w: W, h: H, anchor: 'tl',
      update(lt) {
        X.setTransform(1, 0, 0, 1, 0, 0);
        X.clearRect(0, 0, KW, KH);
        const prev = GLOBALS.map((k) => G[k]);
        Object.assign(G, { X, BG: c.bg, INK: c.ink, ACC: c.acc, CLAY: c.clay, MUT: c.mut, FONT: spec.font || 'Cairo' });
        try {
          for (const d of spec.draw || []) { X.save(); G.MK[d.fn](lt, d); X.restore(); }
        } finally {
          GLOBALS.forEach((k, i) => { G[k] = prev[i]; });
        }
      },
    };
  };
})();
