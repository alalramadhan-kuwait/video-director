#!/usr/bin/env python3
"""Make a whole film from a film file:  python3 tools/make_film.py films/panerai.yaml OUT_DIR [--stills-only] [--voice-dir DIR]
--voice-dir DIR: the narration read elsewhere, one DIR/<id>.wav per line (OmniVoice: tools/voice_script.py, then
omnivoice_narrate.py --lines-dir DIR), instead of the free draft voice.
Prints what Whisper did not hear, layout faults, words under the platform's buttons, how many cuts land on the music's
beats, the stills to look at, the film, its size, the cover or parts the platform needs and the credits file."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import quickfilm

ap = argparse.ArgumentParser(); ap.add_argument('film'); ap.add_argument('out'); ap.add_argument('--stills-only', action='store_true')
ap.add_argument('--voice-dir', default=None, help='one <line id>.wav per line, read elsewhere (OmniVoice)')
a = ap.parse_args()
r = quickfilm.make(a.film, Path(a.out), video=not a.stills_only, voice_dir=a.voice_dir and Path(a.voice_dir))
for ln in r['lines']:
    if ln['not_heard']: print(f"{ln['id']}: not heard → {' '.join(ln['not_heard'])}   (heard: {ln['heard']})")
for slot, p in r['photos'].items():
    print(f"photo {slot}: " + ('MISSING — ' + p['query'] if p.get('missing') else p['credit']))
print('story:', 'all rules kept' if not r['story'] else '\n  ' + '\n  '.join(r['story']))
print('layout:', 'no faults' if not r['layout'] else '\n  ' + '\n  '.join(r['layout']))
print('quality:', 'contrast, overlaps, first frame and motion all pass' if not r.get('quality') else '\n  ' + '\n  '.join(r['quality']))
print(f"platform: {r['platform']}" + (f"  ⚠ {r['length']}" if r.get('length') else ''))
print('safe zones:', 'nothing under the app\'s buttons' if not r['safe'] else '\n  ' + '\n  '.join(r['safe']),
      f"({r['safe_caution']} in the caution band)" if r.get('safe_caution') else '')
print('music:', r['music']['title'] if r['music'] else 'none',
      f"— {r['beats']['on_beat']} of {r['beats']['cuts']} cuts on a beat (music shifted {r['beats']['offset']:+.2f} s)" if r.get('beats') else '')
print('voice:', r['label'])
print(f"{r['seconds']} s" + (f"  {r['film']}  {r['size_mb']} MB" if r.get('film') else '  (stills only)'))
print('stills:', Path(r['stills'][0]).parent, '\ncredits:', Path(a.out) / 'credits.txt')
if r.get('cover'): print('cover:', r['cover'])
for p in r.get('parts', []): print('part:', p)
