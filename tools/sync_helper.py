"""Local-application side of the sync end-to-end test (tools/sync_e2e_test.mjs). Run with VD_DASHBOARD_VAR set to a
COPY of the event log; never the real one.

    python tools/sync_helper.py build OUT_DIR            static Artifact copy (mode 'artifact') from the copy's log
    python tools/sync_helper.py local ITEM DECISION      a decision made in the local app (now)
    python tools/sync_helper.py ingest EXPORT RECEIPTS   ingest an export, write receipts, print the result
    python tools/sync_helper.py events                   decision + sync events, as JSON
"""
import json, sys
from director.dashboard import build as B, serve, sync

cmd, args = sys.argv[1], sys.argv[2:]
if cmd == 'build':
    print(len(B.build_static(args[0])))
elif cmd == 'local':
    print(json.dumps(serve.decide(B.log(), args[0], args[1])))
elif cmd == 'ingest':
    res = sync.ingest(B.log(), sync.load_export(args[0]), 'artifact')
    open(args[1], 'w', encoding='utf-8').write(json.dumps(sync.receipts_for_page(res), ensure_ascii=False))
    print(json.dumps(res, ensure_ascii=False))
elif cmd == 'events':
    rows = [{'seq': r['seq'], 'kind': r['kind'], 'status': r['status'], **{k: r['data'].get(k) for k in ('item', 'decision_id', 'origin', 'reason')}}
            for r in B.log().rows() if r['kind'] in ('review_decided', 'sync')]
    print(json.dumps(rows))
else:
    sys.exit(f'unknown command {cmd}')
