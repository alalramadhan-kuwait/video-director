#!/usr/bin/env python3
"""The independent critic's pack and ledger (director/critic.py).
  python3 tools/critic.py pack OUT_DIR [--purpose "..."]      the next round: sheets, cut strips, measures, brief
  python3 tools/critic.py record OUT_DIR ROUND [--changed "..."]   add the critic's findings.json to the ledger
Give the round folder to a fresh agent that has seen none of the building (it reads brief.md and writes findings.json)."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from director import critic

ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
p = sub.add_parser('pack'); p.add_argument('out'); p.add_argument('--purpose', default='')
r = sub.add_parser('record'); r.add_argument('out'); r.add_argument('round'); r.add_argument('--changed', default='')
a = ap.parse_args()
if a.cmd == 'pack':
    rd = critic.pack(Path(a.out), a.purpose)
    print(rd); print('brief:', rd / 'brief.md')
else:
    e = critic.record(Path(a.out), Path(a.out) / 'critic' / a.round, a.changed)
    print(f"{e['round']}: {e['verdict']}, {len(e['problems'])} problem(s)")
    for p in e['problems']: print(f"  {p.get('rank')}. [{p.get('severity')}] {p.get('at')} scene {p.get('scene')}: {p.get('what')}")
