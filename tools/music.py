#!/usr/bin/env python3
"""The brand's music library: every track it may use (its own licensed tracks, then the whole Kevin MacLeod catalogue,
CC BY 4.0), chosen by the brand's mood and the film's length.
    python3 tools/music.py pick --seconds 150 --seed <film> [--save DIR]   the track the film would get (downloaded with --save)
    python3 tools/music.py search calm piano [--seconds 150]               tracks that fit the brand, best first
    python3 tools/music.py get "Gymnopedie No. 1" [--save DIR]             one named track
Prints the title, licence, source and the credit line that goes in the post caption."""
import argparse, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import brand as B

ap = argparse.ArgumentParser()
ap.add_argument('cmd', choices=('pick', 'search', 'get'))
ap.add_argument('words', nargs='*')
ap.add_argument('--seconds', type=float)
ap.add_argument('--seed', default='')
ap.add_argument('--brand', default='timekeeper')
ap.add_argument('--save')
ap.add_argument('--n', type=int, default=15)
a = ap.parse_args()


def show(t):
    print(f"{t['title']}  ({t.get('seconds') or '?'} s, {', '.join(t.get('feel') or [])}; {t.get('instruments', '')})\n"
          f"  licence: {t['licence']}   source: {t['source']}\n  credit: {t['credit'].replace(chr(10), ' / ')}")


if a.cmd == 'search':
    want = [w.lower() for w in a.words]
    hits = [t for t in B.ranked(a.brand, a.seconds)
            if all(w in f"{t['title']} {' '.join(t.get('feel') or [])} {t.get('instruments', '')} {t.get('about', '')}".lower() for w in want)]
    for t in hits[:a.n]: show(t)
    print(f'{len(hits)} tracks fit the brand' + (f' and «{" ".join(a.words)}»' if want else ''))
    sys.exit(0 if hits else 1)

t = B.choose(a.brand, a.seconds, a.seed) if a.cmd == 'pick' else B.choose(a.brand, title=' '.join(a.words))
if not t:
    print('no licensed track found'); sys.exit(1)
show(t)
if a.save:
    f = B.fetch(t)
    if not f:
        print('could not download it (offline?)'); sys.exit(1)
    d = Path(a.save); d.mkdir(parents=True, exist_ok=True)
    for src in (f, f.with_suffix('.licence.json')):
        if src.is_file(): shutil.copy2(src, d / src.name)
    print('saved', d / f.name)
