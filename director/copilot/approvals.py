"""Approval engine: what each owner gate is deciding right now, and whether an earlier approval still holds.

An approval record (cp_gate event) keeps: project, gate, the item and version it was given for (ref), the content
hash of exactly what was shown, the settings hash (what it depended on upstream), who, when, the note and any
acknowledgements. It is valid only while the content it named is still the content in use AND its upstream still
holds. Nothing carries over to changed content; when something changes, only the gates that depend on it become
outdated, and the earlier approved output stays in use until its replacement is reviewed.

States (for gates and stages): not_started, working, ai_review, needs_owner, changes_requested, owner_approved,
blocked, outdated, completed. "AI reviewed" is never shown as "owner approved".
"""
from __future__ import annotations
import hashlib, json

GATES = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6']
GATE_NAME = {'G1': ('Story direction', 'اتجاه القصة'), 'G2': ('Script and hook', 'النص والافتتاحية'), 'G3': ('Voice', 'الصوت'),
             'G4': ('Visual style', 'الأسلوب البصري'), 'G5': ('Final creative approval', 'الموافقة الإبداعية'),
             'G6': ('Paid narration', 'التعليق المدفوع')}
STATES = ['not_started', 'working', 'ai_review', 'needs_owner', 'changes_requested', 'owner_approved', 'blocked', 'outdated', 'completed']
STATE_NAME = {'not_started': ('Not started', 'لم يبدأ'), 'working': ('Working', 'قيد العمل'), 'ai_review': ('AI review', 'مراجعة الذكاء'),
              'needs_owner': ('Needs your decision', 'ينتظر قرارك'), 'changes_requested': ('Changes requested', 'طُلبت تعديلات'),
              'owner_approved': ('Approved by you', 'وافقتَ عليه'), 'blocked': ('Blocked', 'متوقف'), 'outdated': ('Outdated', 'قديم'),
              'completed': ('Completed', 'اكتمل')}
DEPENDS = {'G1': [], 'G2': ['G1'], 'G3': ['G2'], 'G4': [], 'G5': ['G2', 'G3', 'G4'], 'G6': ['G5']}


def h(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def settings_of(cp) -> dict:
    s = cp['settings']
    return {k: s.get(k) for k in ('duration_s', 'format', 'platform')}


def current(st) -> dict:
    """gate -> {'ref', 'hash'} for what the owner would be deciding now (None: nothing to decide yet)."""
    cp = st['copilot']
    out = {g: None for g in GATES}
    if cp['directions']:
        d = cp['directions'][-1]
        out['G1'] = {'ref': d['v'], 'hash': h('G1', d['file'], d['research_file'], settings_of(cp))}
    if st['scripts']:
        sv = st['scripts'][-1]
        out['G2'] = {'ref': sv['v'], 'hash': h('G2', sv['file'], st['hooks']['selected'])}
    vl = st['voice'].get('lines') or {}
    if vl and all(x['take'] and x['status'] not in ('stale', 'missing') for x in vl.values()):
        from .voicekit import effective_takes
        eff = effective_takes(st)
        out['G3'] = {'ref': 'takes', 'hash': h('G3', sorted(eff.items())), 'takes': eff,
                     'pending': [k for k, t in eff.items() if st['voice']['takes'][t]['status'] != 'approved']}
    if cp['styles']:
        s = cp['styles'][-1]
        out['G4'] = {'ref': s['n'], 'hash': h('G4', s['file'])}       # the choice itself is part of the approval record
    films = [f for f in cp['films'] if f.get('state') == 'ok']
    if films:
        f = films[-1]
        out['G5'] = {'ref': f['n'], 'hash': h('G5', f['render_file'], f['scenes'])}
    if st['gate']['plan']:
        out['G6'] = {'ref': st['gate']['plan']['hash'], 'hash': st['gate']['plan']['hash']}
    return out


def last(cp, g, decision=None):
    recs = [r for r in cp['gates'][g] if decision is None or r['decision'] == decision]
    return recs[-1] if recs else None


def upstream_hash(st, g, valid: dict) -> str:
    """What a gate's approval depends on: the approved content of the gates it builds on (at the time of approval)."""
    cp = st['copilot']
    parts = []
    for u in DEPENDS[g]:
        a = last(cp, u, 'approved')
        parts.append((u, a['content_hash'] if a else None, (a or {}).get('style')))     # a different style choice counts as a change
    return h(g, parts)


def validity(st) -> dict:
    """gate -> {'valid': bool, 'why': str|None, 'approved': record|None}. Upstream first, so a change flows down."""
    cp = st['copilot']
    cur = current(st)
    out = {}
    for g in GATES:
        a = last(cp, g, 'approved')
        if a is None:
            out[g] = {'valid': False, 'why': None, 'approved': None}; continue
        why = None
        c = cur[g]
        if g == 'G3':
            vl = st['voice'].get('lines') or {}
            changed = [k for k, x in vl.items() if x['status'] != 'approved']
            if changed: why = 'lines changed since you approved the voice: ' + ', '.join(changed)
        elif c is None or a['content_hash'] != c['hash']:
            why = {'G1': 'the direction changed (new version or settings)', 'G2': 'a newer script version exists',
                   'G4': 'new style boards were drawn', 'G5': 'the film changed', 'G6': 'the paid plan changed'}[g]
        if not why:
            bad = [u for u in DEPENDS[g] if not out[u]['valid']]
            if bad: why = 'depends on ' + ', '.join(bad) + ', which is no longer approved'
            elif a.get('settings_hash') and a['settings_hash'] != upstream_hash(st, g, out):
                why = 'what it was built on was approved again with different content'
        out[g] = {'valid': not why, 'why': why, 'approved': a}
    return out
