#!/usr/bin/env python3
"""v6 (L5): is this freshly read record still the one the backfill op was computed from?
  python3 check-version.py <record.json> <if_version>      -> prints «same» and exits 0, or «changed» and exits 1
The record file is the record exactly as read just now (a `{data: …}` wrapper is fine). `if_version` is the op's own value:
the stored version, or `sha256:<16 hex>` of the record (keys sorted, UTF-8), as backfill.py computes it."""
import json, sys, hashlib
if len(sys.argv) != 3: print(__doc__); sys.exit(2)
j = json.load(open(sys.argv[1])); want = sys.argv[2]
d = j.get('data', j)
stored = (j.get('_version', j.get('version')) if 'data' in j else j.get('_version'))
h = 'sha256:' + hashlib.sha256(json.dumps(d, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
same = want == h or (stored is not None and str(want) == str(stored))
print('same' if same else f'changed (now {h})'); sys.exit(0 if same else 1)
