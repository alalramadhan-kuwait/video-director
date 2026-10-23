#!/usr/bin/env python3
"""Make a whole film from a film file:  python3 tools/make_film.py films/panerai.yaml OUT_DIR [--stills-only]
Prints what Whisper did not hear, layout faults, the stills to look at, the film, its size and the credits file."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import quickfilm

ap = argparse.ArgumentParser(); ap.add_argument('film'); ap.add_argument('out'); ap.add_argument('--stills-only', action='store_true')
a = ap.parse_args()
r = quickfilm.make(a.film, Path(a.out), video=not a.stills_only)
for ln in r['lines']:
    if ln['not_heard']: print(f"{ln['id']}: not heard → {' '.join(ln['not_heard'])}   (heard: {ln['heard']})")
for slot, p in r['photos'].items():
    print(f"photo {slot}: " + ('MISSING — ' + p['query'] if p.get('missing') else p['credit']))
print('story:', 'all rules kept' if not r['story'] else '\n  ' + '\n  '.join(r['story']))
print('layout:', 'no faults' if not r['layout'] else '\n  ' + '\n  '.join(r['layout']))
print('music:', r['music']['title'] if r['music'] else 'none')
print(f"{r['seconds']} s" + (f"  {r['film']}  {r['size_mb']} MB" if r.get('film') else '  (stills only)'))
print('stills:', Path(r['stills'][0]).parent, '\ncredits:', Path(a.out) / 'credits.txt')
