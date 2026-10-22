#!/usr/bin/env python3
"""Render a real preview of every template in the motion catalogue (art/catalogue.yaml), with the layout check.
    python3 tools/motion_catalogue.py OUT_DIR [--photo a_licensed_photo.jpg] [--video]
OUT_DIR gets one still per template (the brand's fonts, a sample caption on screen), catalogue.html (a contact sheet
with each template's status, purpose and layout check) and report.json; --video adds catalogue.mp4 with every
template in turn and the end card. Templates that need a photo use --photo; without one the engine shows its
«REAL PHOTO NEEDED» panel, and the sheet says so."""
import argparse, html, json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director.studio import art, engine
from director.studio.storyboard import _endcard

ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--photo'); ap.add_argument('--video', action='store_true')
ap.add_argument('--dur', type=float, default=4.5)
a = ap.parse_args()
out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
cat = art.catalogue()
if a.photo:
    (out / 'assets').mkdir(exist_ok=True)
    shutil.copyfile(a.photo, out / 'assets' / ('sample_watch' + Path(a.photo).suffix.lower()))

drawn = [t for t in cat if t['status'] in ('implemented', 'experimental') and t['id'] in art.BUILDERS]
scenes = []
for t in drawn:
    sc = art.scene_visual(t['id'], t['example'], t.get('theme', 'tk-bone'), a.dur, banner=t['name_ar'])
    sc.update(dur=a.dur, transition='fade', captions='نص تجريبي للترجمة أسفل الشاشة', captionStart=0.3, captionEnd=a.dur - 0.3)
    scenes.append(sc)
sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': scenes}

faults = {t['id']: [] for t in drawn}
for line in engine.check(sb, out):
    if line.startswith('scene '):
        n = int(line.split()[1].rstrip(':')) - 1
        if 0 <= n < len(drawn): faults[drawn[n]['id']].append(line)
shots = engine.stills(sb, out, [i * a.dur + a.dur * 0.75 for i in range(len(drawn))], scale=0.5)
report = []
for t, f in zip(drawn, shots):
    dst = out / f"{t['id']}.png"; shutil.copyfile(f, dst)
    need = art.NEEDS_ASSETS.get(t['id'], lambda p: [])(t['example'])
    report.append({'id': t['id'], 'status': t['status'], 'purpose': t['purpose'], 'still': dst.name, 'layout_faults': faults[t['id']],
                   'photo': ('sample photo' if a.photo else 'REAL PHOTO NEEDED panel (no --photo)') if need else 'none needed'})
for t in cat:
    if t not in drawn: report.append({'id': t['id'], 'status': t['status'], 'purpose': t.get('purpose', []), 'still': None,
                                      'note': t.get('about') or t.get('reason', '')})
(out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')

if a.video:
    sbv = {**sb, 'scenes': scenes + _endcard(out)}
    p = out / 'catalogue.json'; p.write_text(json.dumps(sbv, ensure_ascii=False), encoding='utf-8')
    engine.video(p, out / 'catalogue.mp4', scale=1.0, extra=('--crf', 26))

LABEL = {'implemented': 'جاهز', 'experimental': 'تجريبي', 'unavailable': 'غير متوفر'}
cards = []
for r in report:
    t = next(x for x in cat if x['id'] == r['id'])
    img = f'<img src="{r["still"]}" alt="{html.escape(t.get("name_ar", r["id"]))}">' if r['still'] else '<div class="none">لا معاينة</div>'
    fault = ''.join(f'<li>{html.escape(x)}</li>' for x in r.get('layout_faults', []))
    cards.append(f'<figure class="{r["status"]}">{img}<figcaption><b>{html.escape(t.get("name_ar", r["id"]))}</b> '
                 f'<code>{r["id"]}</code> · <span class="st">{LABEL[r["status"]]}</span><br>{html.escape(t.get("about") or t.get("reason", ""))}'
                 f'{"<br><i>" + html.escape(t["reason"]) + "</i>" if t.get("reason") and t.get("about") else ""}'
                 f'{"<br>الصورة: " + html.escape(r["photo"]) if r.get("photo") and r["photo"] != "none needed" else ""}'
                 f'{"<ul class=bad>" + fault + "</ul>" if fault else ("<br>✓ لا أخطاء في التخطيط" if r["still"] else "")}</figcaption></figure>')
(out / 'catalogue.html').write_text(f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Motion catalogue</title><style>body{{font:15px/1.6 system-ui;margin:16px;background:#F0F0EC;color:#111}}main{{display:grid;
grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}figure{{margin:0;background:#fff;border:1px solid #ddd;padding:8px}}
img{{width:100%;display:block}}.none{{aspect-ratio:9/16;display:grid;place-items:center;background:#e4e3dd;color:#777}}
.experimental .st{{color:#9a6a00}}.unavailable{{opacity:.6}}.bad{{color:#a12;margin:4px 0;padding-inline-start:18px}}code{{font-size:12px}}</style>
<h1 dir="rtl">قوالب الحركة</h1><main dir="rtl">{"".join(cards)}</main>''', encoding='utf-8')
print(f"{sum(r['status'] == 'implemented' for r in report)} implemented, {sum(r['status'] == 'experimental' for r in report)} experimental, "
      f"{sum(r['status'] == 'unavailable' for r in report)} unavailable; layout faults: {sum(len(r.get('layout_faults', [])) for r in report)}\n{out / 'catalogue.html'}")
