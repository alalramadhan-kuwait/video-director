"""Measure a reference Reel the way the owner asks («the tone of the speaking, the zooms, the camera movement… recorded»):
    python3 tools/reel_measure.py ref.mp4 out_dir [--scene 0.2]

Writes out_dir/measure.json and prints: the shots (cut times from ffmpeg's scene change, each shot's length), the shots
a minute, the voice (Whisper words: words a second, the pauses, loudness and pitch per sentence via
director/narration.measure), how much sound sits under the voice between words (a music or ambience bed), and
contact sheets of each shot's first and last frame (out_dir/sheetN.jpg) to read the camera moves from. The camera
and acting notes are written by looking at the sheets; numbers come from here."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import narration  # noqa: E402


def cuts(video: Path, scene: float) -> list[float]:
    r = subprocess.run(['ffmpeg', '-i', str(video), '-vf', f"select='gt(scene,{scene})',showinfo", '-f', 'null', '-'], capture_output=True, text=True)
    return [float(p.split(':')[1].split()[0]) for p in r.stderr.split('pts_time')[1:] if p.startswith(':')]


def duration(video: Path) -> float:
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video)], capture_output=True, text=True)
    return float(r.stdout.strip())


def audio(video: Path, sr=16000) -> np.ndarray:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(float) / 32768


def words(video: Path) -> list[dict]:
    from faster_whisper import WhisperModel
    m = WhisperModel('small', device='cpu', compute_type='int8')
    segs, _ = m.transcribe(str(video), beam_size=5, word_timestamps=True)
    return [{'start': s.start, 'end': s.end, 'text': s.text.strip(), 'words': [(w.start, w.end, w.word) for w in s.words]} for s in segs]


def sheets(video: Path, shots: list[tuple[float, float]], out: Path) -> list[Path]:
    from PIL import Image, ImageDraw
    fr = out / 'frames'; fr.mkdir(parents=True, exist_ok=True)
    keep = []
    for k, (a, b) in enumerate(shots):
        if b - a < 0.3: continue
        for tag, t in (('a', a + 0.08), ('b', b - 0.12)):
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', str(video), '-frames:v', '1', '-vf', 'scale=180:320', str(fr / f'{k:02d}{tag}.jpg')])
        if (fr / f'{k:02d}b.jpg').exists(): keep.append(k)
    files = []
    for n in range(0, len(keep), 12):
        ks = keep[n:n + 12]; rows = (len(ks) + 5) // 6
        o = Image.new('RGB', (6 * 370, rows * 350), 'white'); d = ImageDraw.Draw(o)
        for i, k in enumerate(ks):
            x, y = (i % 6) * 370, (i // 6) * 350
            for j, tag in enumerate('ab'): o.paste(Image.open(fr / f'{k:02d}{tag}.jpg'), (x + j * 182, y + 22))
            a, b = shots[k]; d.text((x + 4, y + 4), f'#{k + 1} {a:.1f}-{b:.1f}s ({b - a:.1f})', fill='black')
        f = out / f'sheet{n // 12}.jpg'; o.save(f, quality=82); files.append(f)
    return files


def measure(video: Path, out: Path, scene: float = 0.2) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    total = duration(video); c = [0.0] + cuts(video, scene) + [total]
    shots = [(c[i], c[i + 1]) for i in range(len(c) - 1) if c[i + 1] - c[i] >= 0.3]
    lens = np.array([b - a for a, b in shots])
    segs = words(video); ws = [w for s in segs for w in s['words']]
    x = audio(video)
    db = lambda a, b: float(20 * np.log10(np.sqrt((x[int(a * 16000):int(b * 16000)] ** 2).mean()) + 1e-9))
    gaps = [ws[i + 1][0] - ws[i][1] for i in range(len(ws) - 1)]
    span = ws[-1][1] - ws[0][0] if ws else 0
    per = [{'at': round(s['start'], 2), 'text': s['text'], **narration.measure(x[int(s['start'] * 16000):int(s['end'] * 16000)], 16000, len(s['text']))} for s in segs]
    under = [db(ws[i][1] + .03, ws[i + 1][0] - .03) for i in range(len(ws) - 1) if gaps[i] > .3]
    rep = {'seconds': round(total, 2), 'shots': len(shots), 'per_minute': round(60 * len(shots) / total, 1),
           'shot_seconds': {'mean': round(float(lens.mean()), 2), 'min': round(float(lens.min()), 2), 'max': round(float(lens.max()), 2)},
           'cuts': [round(a, 2) for a, _ in shots[1:]],
           'voice': {'words': len(ws), 'words_per_second': round(len(ws) / span, 2) if span else 0,
                     'pauses_over_0.25': int(sum(g > .25 for g in gaps)), 'longest_pause': round(max(gaps), 2) if gaps else 0,
                     'speech_db': round(float(np.median([db(w[0], w[1]) for w in ws if w[1] - w[0] > .15])), 1),
                     'under_voice_db': round(float(np.median(under)), 1) if under else None, 'sentences': per},
           'sheets': [str(f) for f in sheets(video, shots, out)]}
    (out / 'measure.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
    return rep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0]); ap.add_argument('video'); ap.add_argument('out'); ap.add_argument('--scene', type=float, default=0.2)
    a = ap.parse_args(argv)
    r = measure(Path(a.video), Path(a.out), a.scene)
    v = r['voice']
    print(f"{r['seconds']} s · {r['shots']} shots ({r['per_minute']}/min) · shot {r['shot_seconds']}")
    print(f"voice: {v['words']} words, {v['words_per_second']}/s, {v['pauses_over_0.25']} pauses, longest {v['longest_pause']} s, "
          f"speech {v['speech_db']} dB, under the voice {v['under_voice_db']} dB")
    for s in v['sentences']: print(f"  {s['at']:6.2f}  {s['loud']:6.1f} dB  {s['pitch'] or 0:6.1f} Hz  {s['pace']:5.1f} c/s  {s['text']}")
    for f in r['sheets']: print('SHEET:' + f)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
