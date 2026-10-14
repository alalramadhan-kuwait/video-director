"""Build a HyperFrames composition of Diabetes ep7 scene a3 from the SAME inputs as our engine:
approved narration (l4, l5), their word timings, the ep7 palette and fonts. Evaluation only."""
import json, sys
S, OUT = sys.argv[1], sys.argv[2]
t = json.load(open(f'{S}/ep7/p1/timeline.json'))
sc = next(s for s in t['scenes'] if s['id'] == 'a3'); T0 = sc['start']; DUR = round(sc['end'] - T0, 3)
vo = {v['id']: v for v in t['vo'] if v['id'] in ('l4', 'l5')}
W = {k: [(w.get('w') or w.get('text'), round(w['s'] - T0, 3), round(w['e'] - T0, 3)) for w in v['words']] for k, v in vo.items()}
P = {"bg": "#1C3550", "ink": "#FFF8EE", "acc": "#F2B84B", "clay": "#C98A12", "hi": "#FFE39A", "mut": "#B8CADB"}
RED, BLUE, MINT, PAPER = '#FF5A5F', '#4E7FD1', '#8FF7E8', '#EFE3C8'
chunks = [('l4', [0, 1, 2, 3, 4, 5]), ('l4', [6, 7, 8, 9, 10, 11, 12]), ('l5', [0, 1, 2, 3, 4]), ('l5', [5, 6, 7, 8, 9])]
hot = {'l4': {0, 5, 7, 9, 11}, 'l5': {1, 3, 4, 6, 8, 9}}
a = lambda i: W['l4'][i]; b = lambda i: W['l5'][i]
cap_html, cap_js = [], []
for ci, (ln, ix) in enumerate(chunks):
    s0 = W[ln][ix[0]][1] - 0.02
    nxt = chunks[ci + 1] if ci + 1 < len(chunks) else None
    e0 = (W[nxt[0]][nxt[1][0]][1] - 0.02) if nxt and nxt[0] == ln else W[ln][ix[-1]][2] + 0.02
    words = ''.join(f'<span class="w{" hot" if g in hot[ln] else ""}" id="w-{ln}-{g}">{W[ln][g][0]}</span> ' for g in ix)
    cap_html.append(f'<div class="cap clip" id="cap{ci}" data-start="{s0:.3f}" data-duration="{e0 - s0:.3f}"><p class="capbox" dir="rtl">{words}</p></div>')
    for g in ix:
        ws = W[ln][g][1]
        cap_js.append(f'tl.fromTo("#w-{ln}-{g}", {{opacity:0, y:50}}, {{opacity:1, y:0, duration:0.34, ease:"expo.out"}}, {ws - 0.08:.3f});')
        if g in hot[ln]:
            cap_js.append(f'tl.fromTo("#w-{ln}-{g}", {{"--u":0}}, {{"--u":1, duration:0.35, ease:"expo.out", immediateRender:false}}, {ws + 0.1:.3f});')
S_mid = b(0)[1]
html = f'''<!doctype html>
<html lang="ar">
<head>
<meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
<title>ep7 a3 · HyperFrames evaluation</title>
<script src="assets/gsap.min.js"></script>
<style>
@font-face {{ font-family: "Cairo"; src: url("assets/Cairo-VF.ttf"); font-weight: 200 1000; }}
@font-face {{ font-family: "Plex Arabic"; src: url("assets/IBMPlexSansArabic-Bold.ttf"); font-weight: 700; }}
@font-face {{ font-family: "Plex Arabic"; src: url("assets/IBMPlexSansArabic-Regular.ttf"); font-weight: 400; }}
body {{ margin: 0; background: {P["bg"]}; color: {P["ink"]}; font-family: "Plex Arabic", sans-serif; }}
#root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: radial-gradient(circle at 50% 45%, rgba(143,247,232,.22), transparent 55%), {P["bg"]}; }}
.full {{ position: absolute; inset: 0; }}
.chrome {{ position: absolute; top: 70px; left: 0; right: 0; display: flex; flex-direction: column; align-items: center; gap: 10px; }}
.series {{ font: 800 50px "Cairo"; color: {P["ink"]}; }}
.ep {{ font: 700 26px "Plex Arabic"; color: {P["mut"]}; }}
.sect {{ margin-top: 18px; font: 700 40px "Plex Arabic"; padding: 6px 28px; border: 2px solid rgba(255,248,238,.35); border-radius: 16px; background: rgba(255,248,238,.06); }}
.card {{ position: absolute; left: 220px; top: 780px; width: 640px; height: 480px; background: {PAPER}; border-radius: 14px; box-shadow: 0 18px 44px rgba(0,0,0,.45); }}
.card svg {{ width: 100%; height: 100%; display: block; }}
.chip {{ position: absolute; transform-origin: center; display: block; white-space: nowrap; font: 700 46px "Plex Arabic"; padding: 6px 30px; border-radius: 40px; }}
.sugar {{ position: absolute; left: 470px; top: 760px; width: 140px; height: 560px; border-radius: 70px; border: 6px solid {P["ink"]}; overflow: hidden; background: rgba(0,0,0,.25); }}
.sugar .lvl {{ position: absolute; left: 0; right: 0; bottom: 0; height: 100%; background: {P["acc"]}; transform-origin: bottom; }}
.cap {{ position: absolute; left: 0; right: 0; top: 1400px; display: flex; justify-content: center; }}
.capbox {{ margin: 0; max-width: 900px; padding: 18px 36px 26px; border-radius: 26px; background: rgba(28,53,80,.74); box-shadow: 0 0 40px rgba(0,0,0,.45); font: 700 54px/1.3 "Plex Arabic"; text-align: center; }}
.w {{ display: inline-block; position: relative; }}
.w.hot {{ color: {P["acc"]}; --u: 0; }}
.w.hot::after {{ content: ""; position: absolute; right: 0; bottom: -4px; height: 6px; width: calc(var(--u) * 100%); border-radius: 3px; background: {P["acc"]}; opacity: .85; }}
</style>
</head>
<body>
<div id="root" data-composition-id="a3" data-start="0" data-width="1080" data-height="1920" data-duration="{DUR}">
  <audio id="vo-l4" src="assets/l4.wav" data-start="{vo['l4']['start'] - T0:.3f}" data-duration="{vo['l4']['dur']:.3f}" data-track-index="5"></audio>
  <audio id="vo-l5" src="assets/l5.wav" data-start="{vo['l5']['start'] - T0:.3f}" data-duration="{vo['l5']['dur']:.3f}" data-track-index="6"></audio>
  <div class="chrome" dir="rtl"><div class="series">قصة السكري</div><div class="ep">الحلقة 7 من 10</div><div class="sect">الإنسولين السريع</div></div>
  <div class="full" id="partA">
    <div class="card"><svg viewBox="0 0 640 480">
      <line x1="70" y1="410" x2="600" y2="410" stroke="#3a3a3a" stroke-width="4"/><line x1="70" y1="410" x2="70" y2="50" stroke="#3a3a3a" stroke-width="4"/>
      <text x="80" y="44" font-family="Plex Arabic" font-weight="700" font-size="26" fill="#3a3a3a" direction="rtl" text-anchor="end">المفعول</text>
      <text x="600" y="448" font-family="Plex Arabic" font-weight="700" font-size="26" fill="#3a3a3a" direction="rtl" text-anchor="start">الساعات</text>
      <path id="curve" d="M70 410 C 150 410, 170 90, 230 90 S 330 390, 420 404 L 600 404" fill="none" stroke="{MINT}" stroke-width="10" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"/>
      <text id="clabel" x="300" y="150" font-family="Plex Arabic" font-weight="700" font-size="28" fill="#1a6b62" direction="rtl" opacity="0">الإنسولين</text>
    </svg></div>
    <div class="chip" id="chipFast" style="left:420px; top:640px; background:{P["acc"]}; color:{P["bg"]}; opacity:0">سريع</div>
    <div class="chip" id="chipEnds" style="left:330px; top:640px; font-size:40px; background:{RED}; color:#fff; opacity:0">ينتهي بعد ساعات</div>
  </div>
  <div class="full" id="partB" style="opacity:0">
    <div class="sugar"><div class="lvl" id="lvl"></div></div>
    <div class="chip" id="chipUp" style="left:90px; top:620px; font-size:36px; background:{RED}; color:#fff; opacity:0">تأخرت ← يرتفع</div>
    <div class="chip" id="chipDown" style="left:640px; top:620px; font-size:36px; background:{BLUE}; color:#fff; opacity:0">زادت ← يهبط</div>
    <svg id="bolt" style="position:absolute; left:640px; top:900px; width:120px; height:180px; opacity:0" viewBox="0 0 60 90"><path d="M34 0 L6 50 H28 L20 90 L54 34 H32 Z" fill="{P["hi"]}"/></svg>
  </div>
  {''.join(cap_html)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
tl.set("#lvl", {{ scaleY: 0.45 }}, 0);
tl.to("#curve", {{ strokeDashoffset: 0, duration: {a(12)[2] - a(4)[1]:.3f}, ease: "none" }}, {a(4)[1]:.3f});
tl.to("#clabel", {{ opacity: 1, duration: 0.3 }}, {a(6)[1]:.3f});
tl.fromTo("#chipFast", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: {a(5)[2] - a(5)[1]:.3f}, ease: "back.out(2)" }}, {a(5)[1]:.3f});
tl.to("#chipFast", {{ opacity: 0, duration: 0.2 }}, {a(8)[1]:.3f});
tl.fromTo("#chipEnds", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2)" }}, {a(9)[1]:.3f});
tl.to("#partA", {{ opacity: 0, duration: 0.5, ease: "power2.inOut" }}, {S_mid - 0.3:.3f});
tl.to("#partB", {{ opacity: 1, duration: 0.5, ease: "power2.inOut" }}, {S_mid - 0.3:.3f});
tl.to("#lvl", {{ scaleY: 0.92, duration: {b(4)[2] - b(1)[1]:.3f}, ease: "power3.out" }}, {b(1)[1]:.3f});
tl.fromTo("#chipUp", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2)" }}, {b(1)[1]:.3f});
tl.to("#lvl", {{ scaleY: 0.12, backgroundColor: "{RED}", duration: {b(9)[2] - b(6)[1]:.3f}, ease: "expo.in" }}, {b(6)[1]:.3f});
tl.fromTo("#chipDown", {{ opacity: 0, scale: 0.4 }}, {{ opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2)" }}, {b(6)[1]:.3f});
tl.fromTo("#bolt", {{ opacity: 0, scale: 0.3 }}, {{ opacity: 1, scale: 1.1, duration: {b(9)[2] - b(8)[1]:.3f}, ease: "back.out(2)" }}, {b(8)[1]:.3f});
{chr(10).join(cap_js)}
window.__timelines["a3"] = tl;
</script>
</body>
</html>'''
open(f'{OUT}/index.html', 'w', encoding='utf-8').write(html)
print('duration', DUR, 'words', sum(len(v) for v in W.values()))
