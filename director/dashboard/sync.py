"""Decisions made on the dashboard Artifact → the local event log, and receipts back to the page.

The path:
  1. the page stores each decision as its own document  decisions/<decision_id>  (never overwritten);
  2. EXPORT: the documents are listed (ArtifactData list, or a future MCP connector) and saved as JSON;
  3. INGEST (this module, run by the local application): every decision gets exactly one outcome:
        recorded   new event in the log (event number returned)
        duplicate  this decision_id, or an identical latest decision for the item, is already in the log
        conflict   the item is locked (approved), or a newer different local decision exists: not applied
        refused    the decision breaks a rule (e.g. a listening answer without proof the audio played)
        failed     the row could not be read or the item is unknown
     Nothing is dropped silently; every non-recorded outcome is also written to the log as a 'sync' event;
  4. RECEIPTS: one document per decision  sync/<decision_id>  goes back to the page. Only then does the page show
     the decision as recorded. Until a receipt arrives the page says "saved on this page, not yet in the event log".
Running ingest again on the same export changes nothing (idempotent): recorded decisions come back as 'duplicate'
with the original event number.
"""
from __future__ import annotations
import json, time
from datetime import datetime, timezone
from pathlib import Path

from ..events import EventLog
from . import build as B
from .playback import check_listening_evidence, LISTENING

OUTCOMES = ('recorded', 'duplicate', 'conflict', 'refused', 'failed')


def _ts(at) -> float | None:
    """ISO time -> seconds. Event-log times have no milliseconds and page times do, so they are compared as
    instants, never as text ('12:32:52Z' sorts after '12:32:52.500Z' as a string)."""
    try:
        d = datetime.fromisoformat(str(at).replace('Z', '+00:00'))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except (TypeError, ValueError):
        return None


def load_export(path) -> list[dict]:
    """Accepts a JSON file (list of docs or {docs:[...]}) or a folder written by ArtifactData list --out_dir."""
    p = Path(path)
    if p.is_dir():
        files = sorted((p / 'decisions').glob('*.json')) if (p / 'decisions').is_dir() else sorted(p.glob('*.json'))
        docs = []
        for f in files:
            try:
                d = json.loads(f.read_text(encoding='utf-8'))
            except Exception as e:                                   # unreadable file: reported, not skipped
                docs.append({'_doc': f.stem, '_error': f'unreadable export file: {e}'}); continue
            docs.append({'_doc': f.stem, **(d.get('data', d) if isinstance(d, dict) else {})})
        return docs
    d = json.loads(p.read_text(encoding='utf-8'))
    rows = d.get('docs', d) if isinstance(d, dict) else d
    return [{'_doc': r.get('id') or r.get('decision_id'), **(r.get('data', r))} for r in rows]


def ingest(log: EventLog, docs: list[dict], source: str, snapshot: dict | None = None) -> dict:
    snap = snapshot or B.snapshot()
    targets = {i['id']: i for i in snap['inbox_checks']}               # listening checks know their audio and word
    receipts = []
    for d in sorted(docs, key=lambda r: (_ts(r.get('at')) or 0.0, r.get('_doc') or '')):
        receipts.append(_one(log, d, source, targets))
    summary = {o: sum(1 for r in receipts if r['status'] == o) for o in OUTCOMES}
    log.emit('note', 'dashboard', actor='sync', note=f'ingest from {source}', **summary)
    return {'source': source, 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'summary': summary, 'receipts': receipts}


def _one(log: EventLog, d: dict, source: str, targets: dict) -> dict:
    did = d.get('decision_id') or d.get('_doc')
    rec = {'decision_id': did, 'item': d.get('item'), 'decision': d.get('decision'), 'page_at': d.get('at')}

    def out(status, reason='', seq=None, log_it=True):
        rec.update(status=status, reason=reason, event=seq)
        seen = any(r['data'].get('decision_id') == did and r['status'] == status for r in log.rows(kind='sync'))
        if status != 'recorded' and log_it and not seen:       # a re-run reports it again but logs it once
            log.emit('sync', 'dashboard', actor='sync', status=status, decision_id=did, item=d.get('item'), reason=reason, origin=source)
        return rec

    if d.get('_error') or not did:
        return out('failed', d.get('_error') or 'decision has no id')
    prior = [r for r in log.rows(kind='review_decided')]
    same_id = next((r for r in prior if r['data'].get('decision_id') == did), None)
    if same_id:
        return out('duplicate', 'already recorded', same_id['seq'], log_it=False)
    item, decision = d.get('item') or '', d.get('decision') or ''
    try:
        project, video, scene = B.locate(item)
    except ValueError as e:
        return out('failed', str(e))
    from .serve import DECISIONS
    if decision not in DECISIONS:
        return out('refused', f'unknown decision {decision!r}')
    if decision in LISTENING:
        ok, why = check_listening_evidence(targets.get(item), d.get('playback'))
        if not ok:
            return out('refused', 'not a confirmed listening result: ' + why)
    hist = [r for r in prior if r['data'].get('item') == item]
    last = hist[-1] if hist else None
    if last and last['status'] == decision and (last['data'].get('note') or '') == (d.get('note') or ''):
        return out('duplicate', f'same decision already recorded as event #{last["seq"]}', last['seq'])
    if last and last['status'] == 'approved' and decision != 'changes_requested':
        return out('conflict', f'item is approved and locked (event #{last["seq"]}); request changes instead')
    page_t = _ts(d.get('at'))
    last_t = (_ts(last['data'].get('page_at')) or _ts(last['at'])) if last else None   # when it was decided, not when it was filed
    if last and page_t is None:
        return out('failed', f'decision time {d.get("at")!r} is not a valid time')
    if last and last_t is not None and page_t < last_t and last['status'] != decision:
        return out('conflict', f'a newer decision ({last["status"]}, event #{last["seq"]}) was made after this one; not applied')
    seq = log.emit('review_decided', project, video=video, scene=scene, status=decision,
                   actor='owner (local app)' if source == 'local app' else 'owner (dashboard page)',
                   item=item, note=(d.get('note') or '')[:2000], decision_id=did, page_at=d.get('at'), origin=source,
                   playback=d.get('playback'))
    return out('recorded', '', seq)


def receipts_for_page(result: dict) -> list[dict]:
    """ArtifactData batch writes: one sync/<decision_id> document per receipt."""
    return [{'op': 'set', 'collection': 'sync', 'doc_id': r['decision_id'],
             'data': {k: r[k] for k in ('decision_id', 'item', 'decision', 'status', 'reason', 'event')} | {'at': result['at']}}
            for r in result['receipts'] if r.get('decision_id')]


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('export'); ap.add_argument('--source', default='artifact')
    ap.add_argument('--receipts', help='write the receipts (ArtifactData batch format) to this file')
    a = ap.parse_args()
    res = ingest(B.log(), load_export(a.export), a.source)
    if a.receipts:
        Path(a.receipts).write_text(json.dumps(receipts_for_page(res), ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(res['summary']))
