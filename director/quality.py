"""The quality bar, measured rather than judged by eye (from the "awesome Opus 5.5 videos" prompts, e.g. a critic that
measures frozen time and contrast and returns problems with time codes):

  contrast   every word against what is really behind it: the paper it sits on, else the frame rendered with the words
             hidden. WCAG levels: 4.5:1, or 3:1 for large text (24 px, or 18.7 px bold, at 720x1280).
  overlap    no words crossing other words (two different pieces of text sharing more than 15 % of the smaller one)
  first      frame one is a finished picture: no words still fading or flying in at t = 0
  frozen     no still stretch: ffmpeg freezedetect on the finished film (a long hold reads as a broken video)
  camera     every scene's camera moves at least 3 % (director/studio/motion.py; the end card rests on purpose)

Each check returns plain lines with the scene and the time, like the layout and safe-zone checks."""
from __future__ import annotations
import json, re, subprocess
from pathlib import Path

from .studio import engine

SAMPLE = 1.0                                   # seconds between measured frames
FREEZE_NOISE, FREEZE_MIN = 0.002, 0.8          # a frame this close to the last one, for this long, is a still


def lum(c) -> float:
    """Relative luminance of an sRGB colour (0-255 channels)."""
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def ratio(a, b) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def need(w: dict) -> float:
    big = w['px'] >= 24 or (w['px'] >= 18.7 and w['weight'] >= 700)
    return 3.0 if big else 4.5


def textmap(sb: dict, work: Path, times: list[float]) -> list[dict]:
    work.mkdir(parents=True, exist_ok=True)
    p = work / '_textmap.json'; p.write_text(json.dumps(sb, ensure_ascii=False), encoding='utf-8')
    out = work / 'textmap'
    engine.run(p, '--textmap', ','.join(f'{t:.2f}' for t in times), '-o', out)
    frames = json.loads((out / 'textmap.json').read_text(encoding='utf-8'))
    for i, f in enumerate(frames):
        f['bare'] = str(out / f'bare_{i}.png')
    return frames


def inner(box, k=0.12):
    """The box without its edges: glyph boxes reach past the ink, into whatever the words sit next to."""
    x0, y0, x1, y1 = box
    dx, dy = (x1 - x0) * k, (y1 - y0) * k
    return [x0 + dx, y0 + dy, x1 - dx, y1 - dy]


def behind(img, box) -> list:
    """The worst-case background in the box: of its darker and lighter tenth, the one nearer the words is used later."""
    x0, y0, x1, y1 = [int(round(v)) for v in inner(box)]
    x0, y0 = max(0, x0), max(0, y0)
    if x0 >= img.width or y0 >= img.height: return []                  # words wholly off the frame (a camera move)
    x1, y1 = min(img.width, max(x0 + 1, x1)), min(img.height, max(y0 + 1, y1))
    px = sorted(img.crop((x0, y0, x1, y1)).getdata(), key=lum)
    return [px[int(len(px) * .1)], px[int(len(px) * .9)]] if px else []


def contrast(frames: list[dict]) -> list[dict]:
    from PIL import Image
    out = []
    for f in frames:
        img = Image.open(f['bare']).convert('RGB')
        for w in f['words']:
            if w['alpha'] < 0.9 or w['box'][2] - w['box'][0] < 0.6 * w['px']:
                continue                                          # entering or leaving, or a lone mark split off by bidi
            bgs = [w['paper']] if w['paper'] else behind(img, w['box'])
            if not bgs:
                continue
            r = min(ratio(w['color'], b) for b in bgs)
            if r < need(w):
                out.append({'kind': 'contrast', 't': f['t'], 'scene': w['scene'], 'what': w['text'], 'ratio': round(r, 2), 'need': need(w)})
    return out


def overlaps(frames: list[dict]) -> list[dict]:
    out = []
    area = lambda b: max(0, b[2] - b[0]) * max(0, b[3] - b[1])
    for f in frames:
        ws = [w for w in f['words'] if w['alpha'] >= 0.9]
        for i, a in enumerate(ws):
            for b in ws[i + 1:]:
                if a['id'] == b['id'] or (a['caption'] and b['caption']):
                    continue
                A, B = inner(a['box']), inner(b['box'])                # touching is not crossing
                ib = [max(A[0], B[0]), max(A[1], B[1]), min(A[2], B[2]), min(A[3], B[3])]
                small = min(area(A), area(B))
                if small and area(ib) / small > 0.15:
                    out.append({'kind': 'overlap', 't': f['t'], 'scene': a['scene'], 'what': f"«{a['text']}» crosses «{b['text']}»"})
    return out


def first_frame(frames: list[dict]) -> list[dict]:
    f0 = next((f for f in frames if f['t'] <= 0.05), None)
    return [{'kind': 'first', 't': 0.0, 'scene': w['scene'], 'what': w['text']} for w in (f0 or {}).get('words', []) if 0.05 < w['alpha'] < 0.9]


def frozen(mp4: Path, noise: float = FREEZE_NOISE, least: float = FREEZE_MIN, ending: float = 0.0) -> list[dict]:
    """Still stretches in the finished film; the last `ending` seconds (the end card, whose logo rests on purpose) are not
    counted."""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(mp4), '-vf', f'freezedetect=n={noise}:d={least}', '-map', '0:v', '-f', 'null', '-'],
                       capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', r.stderr)]
    durs = [float(x) for x in re.findall(r'freeze_duration: ([\d.]+)', r.stderr)]
    if len(starts) > len(durs):                       # a still that runs to the end is never closed: it lasts to the end
        m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
        end = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else starts[-1]
        durs.append(end - starts[-1])
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 1e9
    return [{'kind': 'frozen', 't': round(s, 2), 'seconds': round(d, 2)} for s, d in zip(starts, durs)
            if d >= least and s < total - ending]


def runs(found: list[dict]) -> list[str]:
    """Consecutive samples of the same problem as one line with its time range."""
    out, open_ = [], {}
    for h in sorted(found, key=lambda h: (h['kind'], str(h.get('what')), h['t'])):
        k = (h['kind'], h.get('scene'), h.get('what'))
        e = open_.get(k)
        if e and h['t'] - e['to'] <= SAMPLE * 1.5:
            e['to'] = h['t']; e['ratio'] = min(e.get('ratio', 99), h.get('ratio', 99))
        else:
            e = {**h, 'from': h['t'], 'to': h['t']}; open_[k] = e; out.append(e)
    say = {'contrast': lambda e: f"«{e['what']}» is hard to read: contrast {e['ratio']}:1, needs {e['need']}:1",
           'overlap': lambda e: e['what'],
           'first': lambda e: f"frame one shows «{e['what']}» still coming in (the first frame should be a finished picture)",
           'frozen': lambda e: f"the picture stands still for {e['seconds']} s"}
    return [(f"scene {e['scene'] + 1}  " if e.get('scene') is not None and e['scene'] >= 0 else '') +
            f"{e['from']:.1f}-{e['to']:.1f}s  " + say[e['kind']](e) for e in out]


def camera(sb: dict, least: float | None = None) -> list[str]:
    """Scenes whose camera moves less than `least` (3 %): a picture that stands still while the voice goes on."""
    from .studio import motion
    least = motion.MIN if least is None else least
    out, t = [], 0.0
    for i, s in enumerate(sb.get('scenes', [])):
        d = float(s.get('dur') or 0)
        if not s.get('endcard'):
            a = motion.amount(s, d)
            if a + motion.TOL < least:
                out.append(f"scene {i + 1}  {t:.1f}-{t + d:.1f}s  the camera moves {a * 100:.1f} % (at least {least * 100:.0f} %: a push, a drift or a dolly)")
        t += d
    return out


def check(sb: dict, work: Path, seconds: float) -> list[str]:
    """Contrast, overlap and the first frame on the storyboard (before any video is rendered)."""
    times = [0.0] + [round(SAMPLE * i + .5, 2) for i in range(int(seconds / SAMPLE)) if SAMPLE * i + .5 < seconds - .1]
    frames = textmap(sb, work, times)
    return runs(contrast(frames) + overlaps(frames) + first_frame(frames))
