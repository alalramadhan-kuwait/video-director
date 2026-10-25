"""The independent critic (from the "awesome Opus 5.5 videos" prompts): the builder never judges its own work.

A finished film (a make_film folder) becomes a critic pack in <out>/critic/round-N/:
  sheet-*.jpg        the whole film, one frame a second, with time codes (30 to a sheet)
  cuts-*.jpg         every change of scene, dense: six frames from 0.4 s before the cut to 0.6 s after it
  measures.json      what the tools measured: loudness and peak, still stretches, the quality bar, safe zones, the
                     story check, layout, length for the platform, cuts on the beat, the narration as heard
  brief.md           what the critic is told: the film's purpose, the owner's rules, how to answer; and, from round 2,
                     the previous round's problems, each to be marked fixed, partly fixed or still there
A fresh agent that has seen none of the building reads only the pack and writes findings.json:
  {"verdict": "ship" | "one more pass", "problems": [{"rank", "at", "scene", "what", "why", "fix", "severity"}],
   "previous": [{"id", "status"}]}
`record()` keeps the ledger (<out>/critic/ledger.json): every round, what was found and the numbers before and after.
The critic is told nothing about what the builder believes it fixed; it measures and looks for itself.
"""
from __future__ import annotations
import json, re, subprocess, time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import quality

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
RULES = 'skills/video-director/references/storytelling.md'


def _font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def _frames(mp4: Path, times: list[float], dst: Path, width: int) -> list[Path]:
    dst.mkdir(parents=True, exist_ok=True)
    out = []
    for i, t in enumerate(times):
        f = dst / f'f{i:04d}.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', str(mp4), '-frames:v', '1', '-vf', f'scale={width}:-2',
                        '-q:v', '4', str(f)], check=True)
        out.append(f)
    return out


def _sheet(files: list[Path], labels: list[str], cols: int, dst: Path, mark: list[bool] | None = None):
    ims = [Image.open(f).convert('RGB') for f in files]
    w, h = ims[0].size
    rows = -(-len(ims) // cols)
    sheet = Image.new('RGB', (cols * w, rows * (h + 22)), (24, 24, 24))
    d, fnt = ImageDraw.Draw(sheet), _font(15)
    for i, (im, lab) in enumerate(zip(ims, labels)):
        x, y = (i % cols) * w, (i // cols) * (h + 22)
        sheet.paste(im, (x, y + 22))
        d.text((x + 4, y + 3), lab, fill=(255, 210, 120) if mark and mark[i] else (235, 235, 235), font=fnt)
    sheet.save(dst, quality=82)


def loudness(mp4: Path) -> dict:
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(mp4), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
    i = re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)
    p = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', r.stderr)
    return {'integrated_lufs': float(i[-1]) if i else None, 'true_peak_dbfs': float(p[-1]) if p else None}


def pack(out: Path, purpose: str = '') -> Path:
    """Build the next round's pack from a finished film folder; returns the round folder."""
    out = Path(out)
    film, rep, sb = out / 'film.mp4', json.loads((out / 'report.json').read_text(encoding='utf-8')), json.loads((out / 'film.json').read_text(encoding='utf-8'))
    root = out / 'critic'; root.mkdir(exist_ok=True)
    n = 1 + len([p for p in root.glob('round-*') if p.is_dir()])
    rd = root / f'round-{n}'; rd.mkdir()
    seconds = sum(s['dur'] for s in sb['scenes'])
    starts = [sum(s['dur'] for s in sb['scenes'][:i]) for i in range(len(sb['scenes']))]
    # the whole film, a frame a second
    times = [round(t + .5, 2) for t in range(int(seconds))]
    files = _frames(film, times, rd / '_f', 160)
    for k in range(0, len(files), 30):
        _sheet(files[k:k + 30], [f'{t:.1f}s' for t in times[k:k + 30]], 10, rd / f'sheet-{k // 30 + 1}.jpg')
    # every cut, dense
    cuts = starts[1:]
    strips = []
    for c in cuts:
        ts = [round(max(0, c + d), 2) for d in (-.4, -.2, 0, .2, .4, .6)]
        strips.append((c, ts, _frames(film, ts, rd / '_c' / f'{c:.2f}', 140)))
    for k in range(0, len(strips), 5):
        grp = strips[k:k + 5]
        _sheet([f for _, _, fs in grp for f in fs], [f'{t:.1f}s' + (' CUT' if abs(t - c) < .01 else '') for c, ts, _ in grp for t in ts], 6,
               rd / f'cuts-{k // 5 + 1}.jpg', mark=[abs(t - c) < .01 for c, ts, _ in grp for t in ts])
    for p in (rd / '_f').glob('*'): p.unlink()
    (rd / '_f').rmdir()
    for d in (rd / '_c').glob('*'):
        for p in d.glob('*'): p.unlink()
        d.rmdir()
    (rd / '_c').rmdir()
    measures = {'seconds': round(seconds, 1), 'platform': rep.get('platform'), 'length': rep.get('length'), 'size_mb': rep.get('size_mb'),
                **loudness(film), 'frozen': quality.runs(quality.frozen(film, ending=sum(s['dur'] for s in sb['scenes'][len(rep.get('lines', [])):]))),
                'quality': rep.get('quality', []), 'safe_zones': rep.get('safe', []), 'story': rep.get('story', []), 'layout': rep.get('layout', []),
                'beats': rep.get('beats'), 'voice': rep.get('label'),
                'scenes': [{'n': i + 1, 'id': s.get('id'), 'start': round(st, 2), 'end': round(st + s['dur'], 2),
                            'narration': next((l['heard'] for l in rep.get('lines', []) if l['id'] == s.get('id')), None),
                            'template': next((l['template'] for l in rep.get('lines', []) if l['id'] == s.get('id')), 'end card')}
                           for i, (s, st) in enumerate(zip(sb['scenes'], starts))]}
    (rd / 'measures.json').write_text(json.dumps(measures, ensure_ascii=False, indent=1), encoding='utf-8')
    prev = ledger(out)[-1]['problems'] if ledger(out) else []
    (rd / 'brief.md').write_text(brief(rd, purpose, prev), encoding='utf-8')
    return rd


def brief(rd: Path, purpose: str, previous: list[dict]) -> str:
    sheets = sorted(p.name for p in rd.glob('sheet-*.jpg')); cuts = sorted(p.name for p in rd.glob('cuts-*.jpg'))
    prev = ''
    if previous:
        prev = ('\n## The previous round\'s problems\nFor each, look again and say whether it is fixed, partly fixed or still there '
                '(in "previous"). Do not trust that anything was fixed: check it in the frames.\n' +
                '\n'.join(f"- {p['id']}: {p['at']} — {p['what']}" for p in previous) + '\n')
    return f"""# Critic brief

You are an independent critic of a short Arabic documentary film for Instagram Reels (9:16). You have not seen it
being made. Judge only what is in this folder; measure and look for yourself.

**The film is for:** {purpose or 'Time Keeper, a luxury watch account: a true story of a watch brand, told in order, with real licensed photographs, read by a narrator.'}

**Read:** `measures.json` (what the tools measured: loudness, still stretches, contrast and overlaps, safe zones,
story rules, the narration as Whisper heard it, scene times), the overview sheets {', '.join(sheets)} (a frame a second,
time codes on top), and the cut sheets {', '.join(cuts)} (six frames around every change of scene, the cut frame marked).
The owner's rules are in `{RULES}` (in the repository): judge against them.

**Look for, by time code:** words cut by the frame, unreadable or tiny text, text over faces, a picture that does not
match what is said, a photo of the wrong time, anything that looks broken or unfinished, a cut that jumps (size,
direction or subject do not match), a scene that holds too long or too short to read, sameness (the same layout again
and again), the opening and the ending (do they hook and close?), the brand's look (black, white, gold; no invented
colours), and anything a first-time viewer would not understand with the sound off.
{prev}
**Answer** by writing `findings.json` in this folder, exactly:
```json
{{"verdict": "ship" | "one more pass",
  "problems": [{{"id": "R{rd.name.split('-')[1]}-1", "rank": 1, "at": "12.5s", "scene": 3, "severity": "high|medium|low",
                "what": "what is wrong, in one sentence", "why": "why a viewer would notice", "fix": "the smallest change that fixes it"}}],
  "previous": [{{"id": "R1-1", "status": "fixed|partly fixed|still there"}}]}}
```
Rank the problems, worst first; at most 12. «ship» only if nothing high or medium is left. A video with no bugs is not
the same as a good video: say so if it is dull. Be specific: a time code and a scene number for every problem.
"""


def ledger(out: Path) -> list[dict]:
    p = Path(out) / 'critic' / 'ledger.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else []


def record(out: Path, rd: Path, changed: str = '') -> dict:
    """Add the round's findings to the ledger, with the measured numbers at that round."""
    f = json.loads((Path(rd) / 'findings.json').read_text(encoding='utf-8'))
    m = json.loads((Path(rd) / 'measures.json').read_text(encoding='utf-8'))
    entry = {'round': rd.name, 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'verdict': f.get('verdict'),
             'problems': f.get('problems', []), 'previous': f.get('previous', []), 'changed_before': changed,
             'numbers': {k: m.get(k) for k in ('seconds', 'integrated_lufs', 'true_peak_dbfs', 'size_mb')} |
                        {'quality': len(m.get('quality') or []), 'frozen': len(m.get('frozen') or []), 'safe': len(m.get('safe_zones') or [])}}
    led = ledger(out) + [entry]
    (Path(out) / 'critic' / 'ledger.json').write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding='utf-8')
    return entry
