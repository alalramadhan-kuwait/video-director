"""The final-production gate: everything up to (never including) the paid ElevenLabs run.

plan() shows the owner exactly what a final run WOULD do: the approved narration text line by line, the provider
input after the pronunciation library, the selected voice, model and settings, the billable characters per line
and in total, which lines would reuse an existing approved take, and every blocker. It uses voice/plan.py (the same
plan the gateway checks); the studio never imports the gateway, so nothing here can start a paid call.

Blockers (any one stops authorization):
  * the final voice is not authorized for this film (profile status / approved_for);
  * the narration script, the draft takes, the hook or the art are not approved; review findings or correction tasks
    are open; real photographs are still missing;
  * pronunciation entries the final voice would use are only proposed (not approved by the owner);
  * no budget is set for this project and provider, or the plan exceeds it;
  * paid generation is disabled in this environment (VIDEO_DIRECTOR_PAID_ENABLED is not 1) — always true here.
"""
from __future__ import annotations
import os
from pathlib import Path

from ..library import Library, Entry
from ..ledger import Ledger
from ..voice.plan import build_plan
from ..voice.takes import TakeStore
from .voice import approved_script

PROVIDER = 'elevenlabs'


def research_library(studio, pid, st) -> Library:
    """Names and terms from the research, as the final voice would receive them (Latin letters for names, the Arabic
    word kept where the article must be heard). Status 'proposed' until the owner approves each one."""
    res = studio.research(pid) or {}
    owner = (st['gate'].get('terms') or {})
    entries = []
    for i, t in enumerate(res.get('terms', [])):
        d = owner.get(t['ar'])
        if d == 'arabic' or (d is None and t.get('final', 'latin') != 'latin'):
            continue                                   # sent as written (its article survives)
        entries.append(Entry(id=f'r-{pid}-{i}', scope=f'project:{pid}', surface=t['ar'], status='approved' if d == 'latin' else 'proposed',
                             providers={PROVIDER: {'mode': 'spoken', 'spoken': t['term']}}, note=t.get('note', '')))
    return Library(entries, name=f'research:{pid}')


def ledger(studio) -> Ledger:
    return Ledger(studio.var / 'ledger.sqlite')


def plan(studio, pid) -> dict:
    from .store import Refused
    st = studio.state(pid)
    sv = approved_script(st)
    if sv is None:
        raise Refused('approve the narration script first')
    v = st['voice_profile']
    if not v:
        raise Refused('choose the final voice first')
    if v['provider'] != PROVIDER:
        rec = {'hash': 'none', 'created': '', 'script_v': sv['v'], 'voice': {'name': v['name'], 'provider': v['provider']}, 'voice_status': v['status'],
               'voice_why': v['why'], 'no_paid': True, 'items': [], 'totals': {}, 'chars_total': 0, 'findings': [], 'budget_remaining': None,
               'paid_enabled': False, 'proposed_terms': [],
               'blockers': [f'{v["name"]} is not a paid text-to-speech voice ({v["provider"]}): its final narration is a recorded '
                            f'reading through its own approved workflow, which the Studio does not run'], 'plan': {}}
        studio.act(pid, 'gate_plan', rec, actor='system')
        return rec
    voice = {'provider': v['provider'], 'voice_id': v['voice_id'], 'model': v['model'], 'settings': v['settings'],
             'seed': v['seed'], 'output_format': v['output_format']}
    lib = research_library(studio, pid, st)
    store = TakeStore(studio.pdir(pid) / 'final-takes')
    lines = [{'id': l['id'], 'text': l['text']} for l in studio.read_json(pid, sv['file'])['lines']]
    p = build_plan(pid, lines, voice, lib, store, accept=('approved',))
    L = ledger(studio)
    remaining = L.remaining(pid, PROVIDER)
    blockers = blockers_for(st, v, p, lib, remaining)
    rec = {'hash': p['hash'], 'created': p['created'], 'script_v': sv['v'], 'voice': {'name': v['name'], **voice}, 'voice_status': v['status'],
           'voice_why': v['why'], 'library_version': p['library_version'], 'items': [{k: i[k] for k in ('line', 'action', 'provider_input', 'chars', 'take_key')} for i in p['items']],
           'totals': p['totals'], 'chars_total': p['chars_total'], 'findings': p['findings'], 'budget_remaining': remaining,
           'paid_enabled': os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') == '1', 'blockers': blockers,
           'proposed_terms': [{'surface': e.surface, 'rule': e.providers[PROVIDER]} for e in lib.entries if e.status != 'approved'],
           'overrides': [f"script v{x['v']} was approved over a critical check: {x.get('note_decision', '')}" for x in st['scripts'] if x.get('override') and x['status'] == 'approved'],
           'plan': p}
    studio.act(pid, 'gate_plan', rec, actor='system')
    return rec


def blockers_for(st, v, p, lib, remaining) -> list[str]:
    b = []
    if v['status'] != 'usable':
        b.append(f"final voice {v['name']}: {v['why'] or v['status']}")
    latest = st['scripts'][-1]
    if latest['status'] != 'approved':
        b.append(f"script v{latest['v']} is not approved")
    vl = st['voice'].get('lines') or {}
    stale = [ln for ln, x in vl.items() if x['status'] in ('stale', 'missing')]
    not_ok = [ln for ln, x in vl.items() if x['status'] not in ('approved', 'stale', 'missing')]
    if not st['voice']['takes']:
        b.append('no draft read was reviewed')
    if stale:
        b.append(f'{len(stale)} line(s) have no draft take for their current text: {", ".join(stale[:6])}')
    if not_ok:
        b.append(f'{len(not_ok)} draft line(s) not approved: {", ".join(not_ok[:6])}')
    open_vf = [f for f in st['voice']['flags'] if f['status'] in ('open', 'fix_no_effect')]
    if open_vf:
        b.append(f'{len(open_vf)} pronunciation flag(s) still open: {", ".join(f["word"] for f in open_vf[:4])}')
    sbl = st['storyboards'][-1] if st['storyboards'] else None
    if not (sbl and sbl.get('decision') == 'approved'):
        b.append('storyboard not approved')
    if not (st['hooks']['selected'] and st['hooks']['delivery'] and st['hooks']['delivery']['decision'] == 'delivered'):
        b.append('hook not selected or its payoff not confirmed')
    ok_r = [r for r in st['renders'] if r.get('state') == 'ok']
    if not ok_r or ok_r[-1].get('decision') != 'approved_as_draft':
        b.append('the latest draft film is not approved')
    if ok_r and not any(rv.get('render') == ok_r[-1]['id'] for rv in st['review']['runs']):
        b.append(f'the latest draft film ({ok_r[-1]["id"]}) has not been checked by the independent reviewer')
    open_f = [f for f in st['review']['findings'].values() if not f['decision']]
    if open_f: b.append(f'{len(open_f)} review finding(s) open')
    open_t = [t for t in st['fix_tasks'] if t['status'] == 'open']
    if open_t: b.append(f'{len(open_t)} correction task(s) open')
    unappr = [s for s in st['art']['by_scene'] if s not in st['art']['approved']]
    if unappr: b.append(f'art not approved for {", ".join(unappr)}')
    prop = [e.surface for e in lib.entries if e.status != 'approved']
    if prop: b.append(f'{len(prop)} pronunciation entries for the final voice are only proposed: {", ".join(prop[:5])}')
    if remaining is None:
        b.append(f'no {PROVIDER} budget set for this project')
    elif p['chars_total'] > remaining:
        b.append(f"plan needs {p['chars_total']} characters, budget has {remaining}")
    if os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') != '1':
        b.append('paid generation is disabled in this environment (VIDEO_DIRECTOR_PAID_ENABLED is not 1)')
    return b


def authorization_blockers(studio, pid, st, a) -> list[str]:
    g = st['gate']['plan']
    if not g:
        return ['build the plan first']
    if a.get('plan') != g['hash']:
        return ['the plan changed since it was shown; review the new plan']
    from . import api as _api
    if _api.view(studio.var, pid)['gate'].get('plan_stale'):
        return ['something changed after this plan was built (voice, names, budget, takes or the film); rebuild the plan']
    if not a.get('confirm_text') or a['confirm_text'].strip() != f"{g['chars_total']}":
        return [f"type the number of billable characters ({g['chars_total']}) to confirm"]
    return list(g['blockers'])
