"""Score blind artistic-review output against the ground truth (kept in var/_truth, never shown to the reviewer).
    python tools/art_score.py REQUEST.json TRUTH.json OUT.json RAW.json [RAW.json ...]
Later RAW files replace earlier ones item by item (used when an item was re-reviewed after a test-set fix)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from director.art.artistic import accept_ai_findings, score

req, truth, out, *raws = sys.argv[1:]
req = json.load(open(req)); truth = json.load(open(truth))
merged = {}
for r in raws:
    rows = json.load(open(r))
    for item in {x['scene'] for x in rows}:
        merged[item] = [x for x in rows if x['scene'] == item]
raw = [x for v in merged.values() for x in v]
kept, dropped = accept_ai_findings(raw, req, {'kind': 'model', 'context': 'independent, blind'})
s = score(kept, truth)
for row in s['rows']:
    t = truth[row['item']]; row['hint'] = t['hint']; row['kind'] = t['kind']
    row['severities'] = sorted(f['severity'] for f in kept if f['scene'] == row['item'])
json.dump({'score': s, 'kept': kept, 'dropped': dropped}, open(out, 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in s.items() if k != 'rows'}), 'kept', len(kept), 'dropped', len(dropped))
for r in sorted(s['rows'], key=lambda r: r['item']):
    print(r['item'], r['kind'], r['hint'], 'CAUGHT' if r['caught'] else ('missed' if r['caught'] is False else 'clean'), r['severities'])
