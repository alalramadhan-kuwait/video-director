"""Read what the owner saved on the voice review page and turn it into proposals and decisions.

Input: the page's store rows ({collection: {doc_id: row}}), e.g. from ArtifactData list calls saved as JSON.
Output (nothing else is touched):
  * library proposals   — line-scoped entries with status 'proposed' (never 'approved': approving an entry is a
                          separate owner action in the library);
  * decisions log       — append-only rows: listening answers, take verdicts, word marks;
  * what-if plan        — the cost plan as it WOULD be if every proposal were approved. It is not an approval and
                          the gateway refuses to run it until the owner approves that exact plan.
Approved takes are final in the store: a 'reject' on one becomes a decision 'replace_requested', the take itself and
its status are unchanged.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import yaml

from ..library import Library, Entry
from ..voice.plan import build_plan


def ingest(rows: dict, page_data: dict, library: Library, store, voice: dict, out_dir, by='owner') -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    lines = {l['id']: l for l in page_data['lines']}
    now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    decisions, proposals, notes = [], [], []

    for k, r in (rows.get('listening') or {}).items():
        decisions.append({'kind': 'listening', 'line': r['line'], 'entry': r['entry'], 'written': r['written'],
                          'sent': r['sent'], 'heard': r['heard'], 'take': r['take'], 'take_kind': r.get('take_kind'),
                          'by': by, 'at': r.get('at', now)})

    for k, r in (rows.get('verdicts') or {}).items():
        take = store.get(r['take'])
        if r.get('take_kind') == 'mock' or (take and take['request']['provider'] == 'mock'):
            if store.status(r['take']) == 'candidate':
                store.set_status(r['take'], 'approved' if r['verdict'] == 'approve' else 'rejected', by=by,
                                 reason='voice review page (mock take, interface test)')
            decisions.append({'kind': 'verdict', 'line': r['line'], 'take': r['take'], 'verdict': r['verdict'],
                              'mock': True, 'by': by, 'at': r.get('at', now)})
            continue
        st = store.status(r['take'])
        if st == 'approved' and r['verdict'] == 'reject':
            kind = 'replace_requested'
            notes.append(f"{r['line']}: replacement requested; the approved take stays as it is until a new take is approved")
        elif st == 'approved':
            kind = 'confirmed'
        else:
            kind = r['verdict']
            store.set_status(r['take'], 'approved' if r['verdict'] == 'approve' else 'rejected', by=by, reason=r.get('reason', ''))
        decisions.append({'kind': 'verdict', 'line': r['line'], 'take': r['take'], 'verdict': r['verdict'],
                          'decision': kind, 'reason': r.get('reason', ''), 'by': by, 'at': r.get('at', now)})

    for k, r in (rows.get('marks') or {}).items():
        decisions.append({'kind': 'mark', **{f: r.get(f) for f in ('line', 'wi', 'word', 'time', 'take', 'take_kind', 'type', 'note')},
                          'by': by, 'at': r.get('at', now)})

    for lid, r in (rows.get('corrections') or {}).items():
        if r['option'] == 'leave':
            continue
        line = lines[lid]
        entries = sorted({q['entry'] for q in line['questions'] if q['common_noun']})
        for eid in entries:
            base = next(e for e in library.entries if e.id == eid)
            if r['option'] == 'keep_arabic':
                rule = {'mode': 'keep_arabic'}
            else:   # custom spelling: sent as written by the owner, article responsibility is theirs
                rule = {'mode': 'spoken', 'spoken': r['custom_text'], 'article_ok': True}
            proposals.append(Entry(id=f'prop-{lid}-{eid}', scope=f"project:{page_data['project']}", surface=base.surface,
                                   status='proposed', article='keep', lines=[lid], providers={voice['provider']: rule},
                                   source={'review_page': page_data['plan_hash'], 'correction': lid},
                                   note=(r.get('note') or '') + ' (from the voice review page)'))

    prop_path = out / 'proposals.yaml'
    Library(proposals, name='proposals').dump(prop_path)
    with open(out / 'decisions.jsonl', 'a', encoding='utf-8') as f:
        for d in decisions:
            f.write(json.dumps(d, ensure_ascii=False) + '\n')

    # what-if: the plan if the owner approved every proposal (computed on a copy; proposals stay 'proposed')
    hypo = Library([*library.entries, *[Entry(**{**p.__dict__, 'status': 'approved'}) for p in proposals]], name='what-if')
    script = [{'id': l['id'], 'text': l['approved_text']} for l in page_data['lines']]
    plan = build_plan(page_data['project'], script, voice, hypo, store, accept=('imported', 'approved'))
    plan['what_if'] = True
    (out / 'what_if_plan.json').write_text(json.dumps({k: v for k, v in plan.items() if k != 'findings'},
                                                      ensure_ascii=False, indent=1), encoding='utf-8')
    return {'decisions': len(decisions), 'proposals': [p.id for p in proposals], 'notes': notes,
            'what_if': {'totals': plan['totals'], 'chars_total': plan['chars_total'],
                        'lines': [i['line'] for i in plan['items'] if i['action'] == 'new']},
            'files': [str(prop_path), str(out / 'decisions.jsonl'), str(out / 'what_if_plan.json')]}
