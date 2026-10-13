"""Build the blind test set for the artistic reviewer from real ep7 frames (read-only) + controlled defects.

    python tools/art_testset.py var/art_test

Writes:
  OUT/items/<ID>.jpg        what the reviewer sees (540x960), ids shuffled so they reveal nothing
  OUT/request.json          the review request (metadata, narration, facts, profile) — no ground truth in it
  OUT/../art_truth.json     ground truth, kept OUTSIDE the folder the reviewer is given
Every synthetic defect is drawn on top of a real frame in Chromium; the source frames and videos are never changed.
"""
from __future__ import annotations
import json, random, shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from director.art.artistic import build_request          # noqa: E402
from director import profiles                              # noqa: E402
from tests.fixtures import S                               # noqa: E402

PACK = ROOT / 'var/review/ep7-final'
EP7 = S / 'ep7'
FONT = Path('/home/user/majedphotos/video-ad-editor/video-ad-editor/motion/fonts/Cairo-VF.ttf')
EV = yaml.safe_load((ROOT / 'art/evidence/diabetes-ep7.yaml').read_text(encoding='utf-8'))

CSS = f"""@font-face{{font-family:Cairo;src:url('file://{FONT}')}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}}
.base{{position:absolute;inset:0;width:1080px;height:1920px}}
.pill{{position:absolute;transform:translate(-50%,-50%);font:700 46px Cairo;color:#fff;background:#1d2b40;border:3px solid #c9a35b;border-radius:22px;padding:2px 30px;white-space:nowrap;direction:rtl}}
.chip{{position:absolute;transform:translate(-50%,-50%);font:700 38px Cairo;color:#3a2a00;background:#f3c14b;border-radius:26px;padding:4px 26px;white-space:nowrap;direction:rtl}}
.cap{{position:absolute;left:84px;right:84px;top:1400px;height:112px;background:#1b2636;border-radius:18px;font:700 50px Cairo;color:#fff;display:flex;align-items:center;justify-content:flex-start;padding:0 36px}}
.cap span{{display:inline-block}}"""


def frame(scene, label='mid'):
    return PACK / 'stills' / f'{scene}_{label}.jpg'


def shot(html, out):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'x.html'; p.write_text(f'<!doctype html><meta charset=utf-8><style>{CSS}</style>{html}', encoding='utf-8')
        big = Path(td) / 'x.jpg'
        subprocess.run(['node', str(ROOT / 'tools/html_shot.mjs'), str(p), str(big), '1080', '1920'], check=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(big), '-vf', 'scale=540:960,setsar=1', '-pix_fmt', 'yuvj420p', '-q:v', '3', str(out)], check=True)


def img(scene, extra_style=''):
    return f"<img class=base src='file://{frame(scene)}' style='{extra_style}'>"


def broken(text):
    # isolated letter forms in reversed order: what a renderer without Arabic shaping and bidi produces
    return ''.join(f'<span>{c}</span>' for c in text)


# id_hint, base scene, metadata scene (narration/plan shown to the reviewer), html, truth
SYNTH = [
    ('wrong_year', 'b4', 'b4', img('b4') + "<div class=pill style='left:540px;top:396px'>تورونتو · 1963</div>",
     {'defect': True, 'dimensions': ['accuracy', 'identity'], 'what': 'year card says 1963; the sources say 1936 (Scott & Fisher, zinc)'}),
    ('broken_arabic', 'a3', 'a3', img('a3') + f"<div class=cap style='direction:ltr'>{broken('يعمل بقوة، ثم ينتهي بعد ساعات قليلة')}</div>",
     {'defect': True, 'dimensions': ['arabic_text'], 'what': 'caption rendered with disconnected letters in reversed order'}),
    ('wrong_product', 'd2', 'd2', img('d2') + "<div class=chip style='left:744px;top:1306px;font-size:30px;background:#e9edf2;color:#1b2636;border-radius:8px'>PZI</div>",
     {'defect': True, 'dimensions': ['identity', 'accuracy', 'narration_match'], 'what': 'vial labelled PZI while the narration mixes NPH with fast insulin'}),
    ('narration_mismatch', 'a5', 'd5', img('a5'),
     {'defect': True, 'dimensions': ['narration_match'], 'what': 'frame from a5 (hourglass, syringes) shown for d5 narration (42,000 injections over 58 years)'}),
    ('foreign_palette', 'd3', 'd3', img('d3', 'filter:grayscale(1) sepia(.55) contrast(1.35) brightness(.8)'),
     {'defect': True, 'dimensions': ['style', 'light_colour'], 'what': 'frame recoloured into a sepia/black palette that is not the series palette'}),
    ('stretched_person', 'a1', 'a1', img('a1') + f"<div style=\"position:absolute;left:420px;top:640px;width:270px;height:840px;background:url('file://{frame('a1')}') -420px -640px / 1080px 1920px no-repeat;transform:scaleX(1.7);transform-origin:50% 50%\"></div>",
     {'defect': True, 'dimensions': ['light_colour', 'composition'], 'what': 'Elizabeth stretched 1.7x horizontally (wrong proportions)'}),
    ('face_covered', 'd4', 'd4', img('d4') + "<div class=chip style='left:540px;top:812px;font-size:48px;padding:14px 40px'>ثلاثة أطفال</div>",
     {'defect': True, 'dimensions': ['composition', 'arabic_text', 'light_colour'], 'what': "the label sits on Elizabeth's face"}),
    ('too_dark', 'b3', 'b3', img('b3', 'filter:brightness(.3)'),
     {'defect': True, 'dimensions': ['light_colour', 'composition'], 'what': 'frame far too dark; the microscope view is barely visible'}),
]
REAL = [   # earlier ep7 renders with defects that were found and fixed before the final (cropped, upscaled)
    ('real_name_over_year', EP7 / 'chk/b1cmp.png', 0, 'b1',
     {'defect': True, 'dimensions': ['composition', 'arabic_text'], 'what': 'doctor name overlaps the «الدنمارك · 1936» card (real defect, fixed in the final)'}),
    ('real_chip_under_caption', EP7 / 'chk/p2b.png', 720, 'b1',
     {'defect': True, 'dimensions': ['composition', 'arabic_text'], 'what': 'the «مدة أطول» chip is hidden under the caption card (real defect, fixed in the final)'}),
]
CLEAN = ['a2', 'a4', 'b2', 'b5', 'd5', 'd6']


def main(out):
    out = Path(out); items = out / 'items'
    if out.exists():
        shutil.rmtree(out)
    items.mkdir(parents=True)
    rng = random.Random(7)
    entries = [('synth', *x) for x in SYNTH] + [('real', *x) for x in REAL] + [('clean', s) for s in CLEAN]
    ids = [f'T{n:02d}' for n in range(1, len(entries) + 1)]
    rng.shuffle(ids)
    truth, scenes, pack_scenes = {}, {}, []
    for tid, e in zip(ids, entries):
        dst = items / f'{tid}.jpg'
        if e[0] == 'synth':
            _, hint, base, meta_scene, html, t = e
            shot(html, dst)
        elif e[0] == 'real':
            _, hint, src, x, meta_scene, t = e
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', f'crop=360:640:{x}:0,scale=540:960,setsar=1',
                            '-pix_fmt', 'yuvj420p', '-q:v', '3', str(dst)], check=True)
        else:
            _, meta_scene = e; hint, t = f'clean_{meta_scene}', {'defect': False, 'dimensions': [], 'what': None}
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(frame(meta_scene)), '-vf', 'scale=540:960,setsar=1', '-pix_fmt', 'yuvj420p', '-q:v', '3', str(dst)], check=True)
        truth[tid] = {**t, 'kind': e[0], 'hint': hint, 'metadata_scene': meta_scene}
        m = EV['scenes'][meta_scene]
        scenes[tid] = {'narration': m['narration'], 'plan': m['plan'], 'on_screen_text': m.get('on_screen_text')}
        pack_scenes.append({'id': tid, 'start': 0.0, 'end': 0.0, 'stills': {'mid': f'items/{tid}.jpg'}, 'strip': f'items/{tid}.jpg'})
    pack_scenes.sort(key=lambda s: s['id'])
    prof = profiles.load(ROOT / 'profiles/diabetes-history-sci.yaml')
    req = build_request({'video': None, 'contact': None, 'scenes': pack_scenes}, scenes, prof, EV['facts'])
    req['note'] = ('Each item is ONE still (540x960, from a 1080x1920 vertical video) with the narration and plan of the '
                   'scene it is meant to show. There is no motion evidence in this test, so do not judge motion.')
    (out / 'request.json').write_text(json.dumps(req, ensure_ascii=False, indent=1), encoding='utf-8')
    (ROOT / 'var/_truth/art_truth.json').write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding='utf-8')
    print(len(truth), 'items;', sum(t['defect'] for t in truth.values()), 'with a defect')


if __name__ == '__main__':
    main(sys.argv[1])
