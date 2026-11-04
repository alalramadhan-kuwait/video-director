"""Sign a finished film with the Time Keeper watermark (director/watermark.py), for a film assembled outside make_film
(the AI route); make_film does it by itself when the brand has a `watermark`:
    python3 tools/tk_watermark.py <in.mp4> <out.mp4> [--ending 3.0] [--crf 18]
`--ending` is the end card's length: the mark leaves as the card comes in."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import brand as B, watermark  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--ending', type=float, default=3.0); ap.add_argument('--crf', type=int, default=18)
ap.add_argument('--brand', default=None)
a = ap.parse_args()
cfg = B.load(a.brand)
wm = watermark.config(cfg) or watermark.DEFAULT
logo = B.ROOT / (cfg.get('watermark', {}).get('file') or cfg.get('logo', {}).get('file') or 'vendor/paper-story/tk-logo-512.png')
print(watermark.apply(Path(a.src), Path(a.dst), logo, a.ending, wm, a.crf))
