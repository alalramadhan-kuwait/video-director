/* PM.textAudit(t): every visible run of words at time t, as drawn: its box, colour, size, how visible it is, and the
   solid paper behind it when it sits on one (a banner, a caption tag, a card). video-director, ours.
   Used by render.mjs --textmap for the quality bar (taken from the "awesome Opus 5.5 videos" prompts): words readable
   against what is behind them (contrast), no words crossing other words, and frame one a finished picture. */
(function () {
  const PM = window.PM;
  const rgb = (s) => (String(s).match(/[\d.]+/g) || []).map(Number);
  function look(el) {                                 // the opacity it is shown with, and whether it is fading in or out
    let a = 1;
    for (let e = el; e && e.id !== 'stage'; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
      a *= +cs.opacity;
    }
    return a;
  }
  function paper(el) {                                // the nearest solid background behind the words, if any
    for (let e = el; e && e.id !== 'stage'; e = e.parentElement) {
      const c = rgb(getComputedStyle(e).backgroundColor);
      if (c.length >= 3 && (c.length < 4 || c[3] > 0.9)) return c.slice(0, 3);
    }
    return null;
  }
  PM.textAudit = function (t) {
    PM.setTime(t);
    const out = [], stage = document.getElementById('stage');
    const owner = (n) => n.parentElement.closest('.el, .banner, .cap') || n.parentElement;
    const ids = new Map();
    const settled = PM.scenes.map((sc, si) => {             // a scene mid-transition is partly covered: not measured
      const lt = t - sc.start, trd = si > 0 && sc.spec.transition !== 'cut' ? (sc.spec.transitionDur || 0.45) : 0;
      return lt >= (trd ? trd + 0.05 : 0) && lt <= sc.spec.dur - 0.05;
    });
    const walk = document.createTreeWalker(stage, NodeFilter.SHOW_TEXT);
    for (let n = walk.nextNode(); n; n = walk.nextNode()) {
      const text = n.nodeValue.trim();
      if (!text) continue;
      const el = n.parentElement, a = look(el);
      if (a < 0.05) continue;
      const own = owner(n);
      if (!ids.has(own)) ids.set(own, ids.size);
      const cs = getComputedStyle(el), r = document.createRange(); r.selectNodeContents(n);
      const sc = PM.scenes.findIndex((s) => s.root.contains(el));
      if (sc >= 0 && !settled[sc]) continue;
      for (const b of r.getClientRects()) {
        if (b.width * b.height < 16) continue;
        out.push({ id: ids.get(own), text: text.slice(0, 40), scene: sc, caption: own.classList.contains('cap'),
                   box: [b.left, b.top, b.right, b.bottom].map((v) => +v.toFixed(1)), color: rgb(cs.color).slice(0, 3),
                   size: parseFloat(cs.fontSize) * (b.height / Math.max(1, parseFloat(cs.lineHeight) || b.height)),
                   px: parseFloat(cs.fontSize), weight: +cs.fontWeight || 400, alpha: +a.toFixed(2), paper: paper(el), dir: cs.direction });
      }
    }
    return out;
  };
})();
