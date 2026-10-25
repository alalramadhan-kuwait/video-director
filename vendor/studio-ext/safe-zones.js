/* PM.safeZones(t, zones): the words drawn inside a platform's button zones at time t (video-director, ours).
   zones: [{k, x, y, w, h, hard}] in storyboard pixels (director/platforms.py). Words are measured as the browser lays
   them out (each text run's own boxes, the banner and the captions included), so what is checked is what is drawn.
   A kit canvas (vendor/motion-kit) has no text nodes: its drawn pixels inside a zone are counted instead.
   Idea from video-ad-editor's 08_safe_check.js, which counts the ink a reel draws inside the same zones. */
(function () {
  const PM = window.PM;
  const inter = (a, z) => Math.max(0, Math.min(a.right, z.x + z.w) - Math.max(a.left, z.x)) * Math.max(0, Math.min(a.bottom, z.y + z.h) - Math.max(a.top, z.y));
  function alpha(el) {                                  // the opacity the element is really shown with (0 when hidden)
    let a = 1;
    for (let e = el; e && e.id !== 'stage'; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
      a *= +cs.opacity;
    }
    return a;
  }
  PM.safeZones = function (t, zones) {
    PM.setTime(t);
    const out = [], stage = document.getElementById('stage');
    const scene = (el) => PM.scenes.findIndex((sc) => sc.root.contains(el));
    const walk = document.createTreeWalker(stage, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const text = n.nodeValue.trim();
      if (!text || alpha(n.parentElement) < 0.15) continue;
      const r = document.createRange(); r.selectNodeContents(n);
      for (const b of r.getClientRects()) {
        const a = b.width * b.height;
        if (a < 4) continue;
        for (const z of zones) {
          const f = inter(b, z) / a;
          if (f > 0.3) out.push({ zone: z.k, hard: !!z.hard, what: '«' + text.slice(0, 40) + '»', scene: scene(n.parentElement), t: +t.toFixed(2), pct: Math.round(f * 100) });
        }
      }
    }
    for (const cv of stage.querySelectorAll('canvas')) {
      if (alpha(cv) < 0.15) continue;
      const r = cv.getBoundingClientRect(), kx = cv.width / r.width, ky = cv.height / r.height, X = cv.getContext('2d');
      for (const z of zones) {
        const x0 = Math.max(z.x, r.left), y0 = Math.max(z.y, r.top), x1 = Math.min(z.x + z.w, r.right), y1 = Math.min(z.y + z.h, r.bottom);
        if (x1 <= x0 || y1 <= y0) continue;
        const d = X.getImageData(Math.round((x0 - r.left) * kx), Math.round((y0 - r.top) * ky), Math.max(1, Math.round((x1 - x0) * kx)), Math.max(1, Math.round((y1 - y0) * ky))).data;
        let ink = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 60) ink++;
        const f = ink / (d.length / 4);
        if (f > 0.01) out.push({ zone: z.k, hard: !!z.hard, what: 'a motion-kit drawing', scene: scene(cv), t: +t.toFixed(2), pct: Math.round(f * 100) });
      }
    }
    return out;
  };
})();
