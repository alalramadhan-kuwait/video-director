#!/usr/bin/env python3
"""Find a real photograph on Wikimedia Commons with a free licence stated on its own page.
    python3 tools/find_photo.py "Hans Wilsdorf" [--save DIR]
Prints the file, its licence, author and page (the licence evidence). Same rules as the Co-Pilot: free licences only
(public domain, CC0, CC BY, CC BY-SA), never a replica, and the file's name must hold every distinctive word searched."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director.copilot import commons

ap = argparse.ArgumentParser(); ap.add_argument('query'); ap.add_argument('--save'); ap.add_argument('--all', action='store_true')
a = ap.parse_args()
cands = commons.candidates(a.query)
pick = commons.best(a.query, cands)
for c in (cands if a.all else [pick] if pick else []):
    print(f"{c['title']}\n  licence: {c['licence']}  author: {c['author']}\n  page (evidence): {c['page']}\n  credit on screen: {commons.credit(c)}")
if not pick:
    print('no free-licence photo whose name matches; keep the drawing (or ask the owner for a photo they own)'); sys.exit(1)
if a.save:
    d = Path(a.save); d.mkdir(parents=True, exist_ok=True)
    ext = '.png' if pick['url'].lower().split('?')[0].endswith('.png') else '.jpg'
    out = d / (commons.words(a.query) and '_'.join(commons.words(a.query)) + ext)
    out.write_bytes(commons.fetch(pick['url'])); print('saved', out)
