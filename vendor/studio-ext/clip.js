/* The `video` element: a short clip (an AI-generated scene of people or places, never a watch) played frame-accurately.
   video-director, ours.

     {type: 'video', src: 'assets/l1a_clip.mp4', w: 720, h: 1280, x: 360, y: 640, fit: 'cover', pos: '50% 50%',
      rate: 0.8, end: 'pingpong' | 'hold', from: 0}

   Nothing plays in real time. render.mjs extracts the clip's frames once with ffmpeg (a JPG sequence, cached by the
   file's size and date; headless Chromium has no H.264 decoder and a <video> seek is not frame-accurate there) and
   hands the element `frames: {base, n, fps, w, h}`. The frame shown is a pure function of the scene time, so any frame
   renders the same in any order, on any worker, from any --from:
     clip time c = from + t * rate; past the clip's end it runs backwards at the same rate (ping-pong) and forwards
     again, or holds the last frame (`end: 'hold'`). Between two source frames the next one is laid over at the
     fraction (frame blending), so a clip slowed to 0.7 or a 24 fps clip in a 30 fps film moves smoothly.
   PM.settle() resolves once every frame asked for has been decoded: the renderer awaits it before each screenshot.
   Muted by construction: there is no audio element. */
(function () {
  const PM = window.PM;
  const pending = [];
  PM.settle = function () { const p = pending.splice(0); return Promise.all(p); };

  // the clip's time at scene time t (seconds): played at `rate`, then ping-pong (or hold) past its length `len`
  function clipTime(t, rate, len, end, from) {
    const c = (from || 0) + Math.max(0, t) * (rate || 1);
    if (len <= 0 || c <= len) return Math.max(0, c);
    if (end === 'hold') return len;
    const p = c % (2 * len);
    return p <= len ? p : 2 * len - p;
  }
  PM.clipTime = clipTime;

  PM.builders.video = function (spec, ctx) {
    const w = spec.w || ctx.S.width, h = spec.h || ctx.S.height;
    const node = ctx.div('', { position: 'relative', width: w + 'px', height: h + 'px', overflow: 'hidden', background: '#0B0C0E' });
    const fr = spec.frames;
    if (!fr || !fr.n) {                                  // no frames (the file was not found): a dark panel that says so
      const t = ctx.div('', { position: 'absolute', left: 0, right: 0, top: '46%', textAlign: 'center', color: '#F3F0E8',
                              font: '700 26px Cairo, sans-serif', opacity: 0.8 });
      t.textContent = 'VIDEO CLIP MISSING';
      node.appendChild(t);
      return { w, h, node };
    }
    const mk = () => {
      const im = document.createElement('img');
      im.alt = '';
      im.decoding = 'sync';
      Object.assign(im.style, { position: 'absolute', left: 0, top: 0, width: '100%', height: '100%',
                                objectFit: spec.fit === 'contain' ? 'contain' : 'cover', objectPosition: spec.pos || '50% 50%' });
      node.appendChild(im);
      return im;
    };
    const a = mk(), b = mk();
    const len = Math.max(0, (fr.n - 1) / fr.fps);
    const url = (i) => fr.base + String(i + 1).padStart(5, '0') + '.jpg';
    const show = (im, i) => {
      const u = url(i);
      if (im._u === u) return;
      im._u = u; im.src = u;
      pending.push(im.decode ? im.decode().catch(() => {}) : new Promise((r) => { im.onload = im.onerror = r; }));
    };
    return {
      w, h, node,
      update(lt) {
        const c = clipTime(lt, spec.rate, len, spec.end, spec.from);
        const fi = Math.min(fr.n - 1, c * fr.fps), i0 = Math.floor(fi), k = fi - i0;
        show(a, i0);
        const i1 = Math.min(fr.n - 1, i0 + 1);
        if (k > 0.02 && i1 !== i0) { show(b, i1); b.style.opacity = k.toFixed(3); b.style.display = ''; }
        else b.style.display = 'none';
      },
    };
  };
})();
