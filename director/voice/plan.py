"""Cost plan: what a final-voice run WOULD do, line by line, before anything is generated.

Each line is prepared with the pronunciation library for the chosen provider, turned into a take request, and
looked up in the take store:
  reuse     an approved take with exactly this request exists          -> 0 characters
  review    an unreviewed candidate exists                             -> 0 characters (listen before deciding)
  blocked   the identical request was already rejected                 -> 0 characters (change text/settings first)
  new       nothing generated for this request yet                     -> len(provider_input) characters
The plan hash covers everything that matters, so an approval cannot be reused for a different plan.
"""
from __future__ import annotations
import hashlib, time
from .takes import TakeStore, take_key, canonical


def build_plan(project: str, lines: list[dict], voice: dict, library, store: TakeStore,
               accept=('approved',), only: set[str] | None = None) -> dict:
    items, findings = [], []
    for ln in lines:
        if only and ln['id'] not in only:
            continue
        text_in, fs = library.prepare(ln['text'], voice['provider'], line=ln['id'], accept=accept)
        findings += [f.__dict__ for f in fs]
        req = {**{k: voice[k] for k in ('provider', 'voice_id', 'model', 'settings', 'seed', 'output_format')},
               'provider_input': text_in}
        key = take_key(req)
        st = store.status(key) if store.get(key) else None
        action = {'approved': 'reuse', 'candidate': 'review', 'rejected': 'blocked'}.get(st, 'new')
        items.append({'line': ln['id'], 'take_key': key, 'action': action, 'provider_input': text_in,
                      'chars': len(text_in) if action == 'new' else 0, 'request': req})
    body = {'project': project, 'provider': voice['provider'], 'voice': {k: voice[k] for k in voice if k != 'provider'},
            'library_version': library.version, 'items': items,
            'totals': {a: sum(1 for i in items if i['action'] == a) for a in ('reuse', 'review', 'blocked', 'new')},
            'chars_total': sum(i['chars'] for i in items)}
    return {**body, 'hash': hashlib.sha256(canonical(body)).hexdigest(), 'findings': findings,
            'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


def plan_hash(plan: dict) -> str:
    """Recompute the hash from the plan's content (detects any edit made after it was shown)."""
    body = {k: plan[k] for k in ('project', 'provider', 'voice', 'library_version', 'items', 'totals', 'chars_total')}
    return hashlib.sha256(canonical(body)).hexdigest()
