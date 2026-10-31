#!/usr/bin/env python3
"""Find a real recorded sound on Openverse (free, no key, no account) with a CC0 or CC BY licence.
    python3 tools/find_sound.py gavel "gavel on wood" [--bed] [--all] [--save DIR] [--fresh] [--no-rank] [--listen WORDS]
Prints the pick (and with --all every candidate): its licence, creator, page (the licence evidence) and the credit
line, then caches it outside git (VD_SFX_CACHE, else ~/.cache/video-director/sfx) as the engine's WAV, trimmed and
levelled, with its licence record. --save DIR copies it as DIR/<name>.wav (<name>_bed.wav with --bed): a film's
<out>/sfx/ folder, where the engine looks before its own kit. In a film file, `sounds: {gavel: "gavel on wood"}` does
the same at render time (director/copilot/sounds.py). Never NC or ND; CC BY sounds go in credits.txt. Openverse is
often slow (504): the tool retries, and when it cannot answer the film keeps the procedural sound (make-sfx.py).
earshot ranks the candidates when it is installed (VD_EARSHOT=/path/to/earshot)."""
import argparse, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director.copilot import sounds

ap = argparse.ArgumentParser()
ap.add_argument('name', help='the sound name a film uses (gavel, train, tower_strike …)')
ap.add_argument('query', help='what to search for, in English ("gavel on wood")')
ap.add_argument('--bed', action='store_true', help='a longer sound that loops under the voice')
ap.add_argument('--all', action='store_true', help='show every candidate, not only the pick')
ap.add_argument('--save', help='copy the pick here as <name>.wav (or <name>_bed.wav)')
ap.add_argument('--fresh', action='store_true', help='search again even if the cache has an answer')
ap.add_argument('--no-rank', action='store_true', help='do not ask earshot to rank the candidates')
ap.add_argument('--listen', help='what earshot should hear, in fuller words ("a wooden gavel striking a block")')
ap.add_argument('--take', type=int, default=4, help='how many candidates to download and compare (default 4)')
ap.add_argument('--timeout', type=float, default=20, help='seconds per Openverse call (default 20; retried on 504)')
a = ap.parse_args()
kind = 'bed' if a.bed else 'shot'
opts = dict(network=True, take=a.take, use_earshot=not a.no_rank, timeout=a.timeout, listen=a.listen)
r = sounds.find(a.query, kind, fresh=a.fresh, **opts)
if not r['pick'] and r['ranked_by'] == 'cache':                     # asked by hand: a recent miss is tried again
    r = sounds.find(a.query, kind, fresh=True, **opts)
pick = r['pick']
for c in ([pick] + r['others'] if a.all and pick else [pick] if pick else []):
    e = c.get('earshot') or {}
    ver = {True: 'confirmed on its page', False: 'page states another licence', None: 'not re-checked (' + str(c.get('verified_how')) + ')'}[c.get('verified')]
    print(f"{c['title']}  [{c['id']}]\n  licence: {c['licence_name']} ({ver})  creator: {c['creator']}"
          f"\n  page (evidence): {c['page']}\n  credit: {c['credit']}\n  file: {c['file']}"
          + (f"\n  earshot: {e.get('verdict')} match (z {e.get('z')}), {e.get('real')} (p_real {e.get('p_real')})" if e else ''))
if not pick:
    print(f"no sound found: {r['why']}\n  the film keeps the procedural {a.name!r} (vendor/paper-story/scripts/make-sfx.py)"); sys.exit(1)
print('ranked by:', r['ranked_by'])
print(f"in the film file:  sounds: {{{a.name}{'_bed' if a.bed else ''}: {a.query!r}}}   or   name: \"found:{pick['id']}\"")
if a.save:
    d = Path(a.save); d.mkdir(parents=True, exist_ok=True)
    out = d / f"{a.name}{'_bed' if a.bed else ''}.wav"
    shutil.copyfile(pick['file'], out); print('saved', out)
