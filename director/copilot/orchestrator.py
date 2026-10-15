"""The Co-Pilot orchestrator: reads the project's events, decides the next piece of free, authorized work, runs it as
a tracked job, and stops at owner gates, exceptions, failures, a pause or a stop.

It keeps no state of its own: `plan()` is a pure function of the event history, so a restarted server finds the
same next step, reuses every output already recorded (content-addressed files, recorded takes, scene versions with
the same inputs) and never generates the same thing twice. A job that was running when the server stopped shows
as interrupted and is simply run again; a job that FAILED blocks its stage until the owner resumes or retries it
(no automatic retries). Spending is never automatic: the AI worker refuses without an owner budget, and paid
narration sits behind Gate 6, which this workspace cannot pass.

Stages and gates
  1 Story direction  → G1     4 Visual style → G4     7 Film → G5
  2 Script and hook  → G2     5 Pictures (exceptions)  8 Paid narration → G6 (locked here)
  3 Voice            → G3     6 Scenes (no owner pause per scene)
While a gate waits for the owner, work that does not depend on it continues (style boards and picture research
while the voice waits, for example), so the next decision is ready sooner.
"""
from __future__ import annotations
import json, os, threading, time
from dataclasses import dataclass, field

from ..studio import jobs, voice as V
from . import ai, approvals as A, factcheck, film as FM, scenes as SC, styles, voicekit

STAGES = [('direction', 'G1', 'Story direction', 'اتجاه القصة'), ('script', 'G2', 'Script and hook', 'النص والافتتاحية'),
          ('voice', 'G3', 'Voice', 'الصوت'), ('style', 'G4', 'Visual style', 'الأسلوب البصري'), ('assets', None, 'Pictures', 'الصور'),
          ('scenes', None, 'Scenes', 'المشاهد'), ('film', 'G5', 'Film', 'الفيلم'), ('paid', 'G6', 'Paid narration', 'التعليق المدفوع'),
          ('export', None, 'Final export', 'التصدير النهائي')]


@dataclass
class Step:
    key: str
    stage: str
    what: str
    fn: object
    args: dict = field(default_factory=dict)
    units: int = 1


# ====================================================================== helpers over state
def done_keys(cp) -> set:
    return {s['key'] for s in cp['stages'] if s.get('state') == 'done' and s.get('key')}


def failed_keys(st) -> dict:
    """key -> error, for steps whose last run failed after the owner last resumed or retried."""
    cp = st['copilot']
    resumed = max([c['seq'] for c in cp['controls'] if c['op'] == 'resume'] + [0])
    out = {}
    for j in st['jobs']:
        if j.get('kind') != 'copilot': continue
        k = (j.get('args') or {}).get('key')
        if not k: continue
        go = max([resumed] + [c['seq'] for c in cp['controls'] if c['op'] == 'retry' and c.get('key') == k])
        if j['state'] != 'failed': out.pop(k, None)
        elif j['seq'] > go: out[k] = j.get('error', 'failed')
    return out


def script_meta(cp, v):
    return cp['script_meta'].get(str(v)) or {}


def merged_check(cp, v):
    return next((c for c in reversed(cp['checks']) if c['target'] == 'script' and c['ref'] == v and c['kind'] == 'merged'), None)


def scene_valid(studio, pid, st, ctx, sid) -> tuple[bool, str]:
    d = st['copilot']['scenes'].get(sid)
    if not d or not d['pick']: return False, 'not made yet'
    if d['pick']['base_hash'] != SC.base_hash(SC.base(studio, pid, st, ctx, sid)): return False, 'outdated: what it shows changed'
    if d['pick']['status'] == 'needs_owner':
        ex = next((x for x in st['copilot']['exceptions'] if x.get('scene') == sid and x.get('version') == d['pick']['n']), None)
        if not ex or ex['status'] == 'open': return False, 'waiting for your decision'
        if ex['decision'] not in ('accept_best',): return False, 'your decision is being applied'
    return True, ''


# ====================================================================== the plan
def plan(studio, pid, st=None) -> dict:
    """What to do next. Returns {'step': Step|None, 'waiting': [gates], 'blocked': [...], 'notes': [...]}."""
    st = st or studio.state(pid)
    cp = st['copilot']
    out = {'step': None, 'waiting': [], 'blocked': [], 'notes': []}
    if cp['mode'] != 'copilot':
        out['notes'].append('manual mode: the Co-Pilot does nothing on its own'); return out
    val = A.validity(st)
    cur = A.current(st)
    done = done_keys(cp)
    fails = failed_keys(st)
    cands: list[Step] = []

    def offer(s: Step):
        if s.key in fails:
            out['blocked'].append({'key': s.key, 'stage': s.stage, 'what': s.what, 'error': fails[s.key]})
        else:
            cands.append(s)

    def wait(g):
        if g not in out['waiting']: out['waiting'].append(g)

    # ---------------------------------------------------------------- 1. direction
    dirs = cp['directions']
    g1_last = A.last(cp, 'G1')
    if not dirs:
        offer(Step('direction:1', 'direction', 'story direction and research (AI)', s_direction, {'v': 1}))
    else:
        d = dirs[-1]
        if not any(c['target'] == 'direction' and c['ref'] == d['v'] for c in cp['checks']):
            offer(Step(f'direction_check:{d["v"]}', 'direction', 'independent research check (AI)', s_direction_check, {'v': d['v']}))
        elif g1_last and g1_last['ref'] == d['v'] and g1_last['decision'] != 'approved':
            offer(Step(f'direction:{d["v"] + 1}', 'direction', 'revise the direction (AI)', s_direction, {'v': d['v'] + 1, 'note': g1_last['note']}))
        elif not val['G1']['valid']:
            wait('G1')
    g1 = val['G1']['valid']
    # ---------------------------------------------------------------- 2. script
    g2 = val['G2']['valid']
    if g1:
        dv = val['G1']['approved']['ref']
        sv = st['scripts'][-1] if st['scripts'] else None
        written = [m for m in cp['script_meta'].values() if m.get('direction_v') == dv]
        if not written:
            offer(Step(f'script:{dv}', 'script', 'write the script and hooks (AI)', s_script_write, {'direction_v': dv}))
        elif sv and sv['status'] == 'draft':
            mc = merged_check(cp, sv['v'])
            meta = script_meta(cp, sv['v'])
            if mc is None:
                offer(Step(f'script_check:{sv["v"]}', 'script', f'fact check and editor review of v{sv["v"]} (AI, independent)', s_script_check, {'v': sv['v']}, 2))
            else:
                bad = [l for l, x in mc['lines'].items() if x['severity'] in ('critical', 'major') and x['verdict'] != 'disputed']
                k = f'script_revise:{sv["v"]}:auto'
                if bad and meta.get('author') == 'ai' and meta.get('round', 0) < cp['settings'].get('max_rounds', 2) and k not in done:
                    offer(Step(k, 'script', f'self-revision of v{sv["v"]} (AI)', s_script_revise, {'v': sv['v'], 'targets': bad, 'owner': False}))
                elif not g2:
                    wait('G2')
        elif sv and sv['status'] in ('changes_requested', 'rejected'):
            g2_last = A.last(cp, 'G2')
            k = f'script_revise:{sv["v"]}:owner'
            if k not in done:
                offer(Step(k, 'script', f'revise v{sv["v"]} as you asked (AI)', s_script_revise,
                           {'v': sv['v'], 'owner': True, 'note': (g2_last or {}).get('note', '')}))
        elif not g2 and sv:
            wait('G2')
    # ---------------------------------------------------------------- 3. voice (and work that does not wait for it)
    g3 = val['G3']['valid']
    brief_v = None
    if g2:
        av = val['G2']['approved']['ref']
        if f'pron:{av}' not in done:
            offer(Step(f'pron:{av}', 'voice', 'pronunciation proposals for names (AI)', s_pron, {'v': av}))
        else:
            vl = st['voice'].get('lines') or {}
            todo = [l for l, x in vl.items() if x['status'] in ('missing', 'stale')]
            if todo:
                offer(Step(f'voice:{av}:{len(st["voice"]["takes"])}', 'voice', f'draft voice for {len(todo)} line(s) (free)', s_voice, {}, len(todo)))
            else:
                takes = voicekit.effective_takes(st)
                nar = {l['id']: l['spoken'] for l in V.narration(studio, pid, st)['lines']}
                tk = st['voice']['takes']
                respell = sorted(l for l, t in takes.items() if t and l in nar and tk[t].get('spoken') != nar[l])
                if respell:                                     # a pronunciation entry changed how a line is read: record it again
                    offer(Step(f'respell:{A.h(sorted((l, nar[l]) for l in respell))}', 'voice',
                               f'new draft takes after a pronunciation change: {", ".join(respell)} (free)', s_respell, {'lines': respell}, len(respell)))
                mix = cp['voice_mix']
                if not mix or mix['takes'] != takes:
                    offer(Step(f'mix:{A.h(takes)}', 'voice', 'play-all narration and voice checks', s_mix, {}, len(takes)))
                elif not g3 or (cur['G3'] and cur['G3']['pending']):
                    wait('G3')                                  # a replacement take waits for you; the approved one stays in use
        for t in cp['adjust']:
            k = f'adjust:{A.h(t)}'
            if k not in done:
                offer(Step(k, 'voice', f'speed/pauses for {t["line"]} (local processing, free)', s_adjust, {'adj': t}))
        # art brief → style boards → picture research
        b_done = [s for s in cp['stages'] if s.get('key', '').startswith(f'brief:{av}') and s.get('state') == 'done']
        if not b_done:
            offer(Step(f'brief:{av}', 'style', 'art brief for every scene (AI)', s_brief, {'v': av}))
        else:
            brief_v = av
            bf = st['art'].get('brief')
            if not cp['styles'] or cp['styles'][-1].get('brief') != bf or cp['styles'][-1].get('registry') != styles.registry()['version']:
                offer(Step(f'styles:{bf}', 'style', 'style boards: real frames of this film in each style', s_styles, {}, 4))
            elif not val['G4']['valid']:
                wait('G4')
            if f'assets:{bf}' not in done:
                offer(Step(f'assets:{bf}', 'assets', 'pictures this film needs (AI)', s_assets, {}))
    g4 = val['G4']['valid']
    rights = [a for a in cp['assets'].values() if a['status'] == 'unverified' and a.get('slot')
              and not any(x['id'] == f'ex-rights-{a["id"]}' for x in cp['exceptions'])]
    for a in rights:
        offer(Step(f'rights:{a["id"]}', 'assets', 'picture without licence evidence', s_rights, {'asset': a['id']}))
    for a in cp['assets'].values():
        x = next((e for e in cp['exceptions'] if e['id'] == f'ex-rights-{a["id"]}' and e['status'] == 'open'), None)
        if x and a['status'] == 'verified':
            offer(Step(f'rights_ok:{a["id"]}', 'assets', 'licence evidence received', s_rights_ok, {'asset': a['id']}))
    # ---------------------------------------------------------------- owner feedback the Co-Pilot cannot act on by itself
    for g in ('G4', 'G5'):
        last = A.last(cp, g)
        if last and last['decision'] != 'approved' and cur[g] and last['content_hash'] == cur[g]['hash']:
            xid = f'ex-fb-{g}-{last["content_hash"][:8]}'
            if not any(x['id'] == xid for x in cp['exceptions']):
                offer(Step(f'feedback:{xid}', 'style' if g == 'G4' else 'film', 'your request → who can do it', s_feedback,
                           {'gate': g, 'note': last.get('note', ''), 'xid': xid}))
    # ---------------------------------------------------------------- comments → tasks
    for t in cp['tasks']:
        if t['status'] == 'open' and t.get('source', '').startswith('comment'):
            offer(Step(f'task:{t["id"]}', 'film', f'your comment at {t.get("t")} s → a change for {t.get("scene") or "the film"} (AI)', s_task, {'task_id': t['id']}))
    # ---------------------------------------------------------------- 6. scenes
    all_valid = False
    if g2 and g3 and g4 and brief_v:
        ctx = SC.context(studio, pid, st)
        order = FM.order(studio, pid, st)
        open_ex = {x['scene'] for x in cp['exceptions'] if x['status'] == 'open' and x.get('scene')}
        states = {}
        for sid in order:
            ok, why = scene_valid(studio, pid, st, ctx, sid)
            states[sid] = ok
            if not ok and sid not in open_ex and why != 'waiting for your decision':
                offer(Step(f'scene:{sid}:{SC.base_hash(SC.base(studio, pid, st, ctx, sid))}', 'scenes', f'scene {sid}: draw, check, review, fix',
                           s_scene, {'scene': sid}, 3))
        all_valid = bool(order) and all(states.values())
        out['scenes'] = states
        # ------------------------------------------------------------ 7. film
        if all_valid:
            films = [f for f in cp['films'] if f.get('state') == 'ok']
            picks = {sid: cp['scenes'][sid]['pick']['n'] for sid in order}
            if not films or films[-1]['scenes'] != picks:
                offer(Step(f'film:{A.h(picks)}', 'film', 'assemble, render and review the film', s_film, {}, 16))
            else:
                f = films[-1]
                k = f'triage:{f["n"]}'
                if k not in done:
                    offer(Step(k, 'film', f'fix what the film review found (film v{f["n"]})', s_triage, {'n': f['n']}))
                elif not val['G5']['valid']:
                    wait('G5')
    # ---------------------------------------------------------------- 8. paid plan (built, never run)
    if val['G5']['valid']:
        from ..studio.api import _plan_stale
        if not st['gate']['plan'] or _plan_stale(st):
            offer(Step(f'plan:{val["G5"]["approved"]["ref"]}:{len(st["history"])}', 'paid', 'final narration plan (nothing is generated)', s_plan, {}))
        else:
            wait('G6')
    out['step'] = cands[0] if cands else None
    out['candidates'] = [c.key for c in cands]
    out['steps'] = cands
    return out


# ====================================================================== steps (each runs as one tracked job)
def _done(studio, pid, key, stage, **res):
    studio.act(pid, 'cp_stage', {'key': key, 'stage': stage, 'state': 'done', **res}, actor='copilot')


def s_direction(studio, pid, task, key, v, note=''):
    st = studio.state(pid)
    out = ai.call(studio, pid, 'direction', {'idea': st['idea'], 'title': st['title'], 'brand': st['brand'], 'note': note,
                                              'duration_s': st['copilot']['settings']['duration_s'], 'format': st['copilot']['settings']['format']})
    if out.get('unsupported'):
        studio.act(pid, 'cp_exception', {'id': f'ex-ai-direction-{v}', 'kind': 'ai', 'scene': None, 'title': 'The AI could not research this idea',
                                         'detail': out['reason'], 'detail_ar': 'الذكاء التجريبي لا يملك بحثًا جاهزًا لهذه الفكرة؛ البحث الحقيقي يحتاج ميزانية توافق عليها',
                                         'options': ['manual', 'retry'], 'pause': True}, actor='copilot')
        return {'unsupported': True}
    studio.act(pid, 'research', {'data': out['research']}, actor='copilot')
    research_file = studio.state(pid)['research']['file']
    doc = {k: out.get(k) for k in ('topic', 'topic_ar', 'angle', 'angle_ar', 'audience', 'duration_s', 'format', 'claims_to_verify', 'note_answer')}
    doc['label'] = out.get('label')
    rec = {'v': v, 'file': studio.put(pid, json.dumps(doc, ensure_ascii=False).encode(), 'json'), 'research_file': research_file,
           'label': out.get('label'), 'mock': bool(out.get('mock')), 'note': note}
    studio.act(pid, 'cp_direction', rec, actor='copilot')
    task.unit(what='direction')
    return {'v': v}


def s_direction_check(studio, pid, task, key, v):
    res = studio.research(pid)
    out = ai.call(studio, pid, 'research_check', {'research': res})
    studio.act(pid, 'cp_check', {'id': f'chk-direction-{v}', 'target': 'direction', 'ref': v, 'kind': 'research', 'findings': out.get('findings', []),
                                 'by': out.get('label')}, actor='reviewer')
    task.unit(what='research check')
    return {}


def s_script_write(studio, pid, task, key, direction_v):
    st = studio.state(pid)
    d = studio.read_json(pid, st['copilot']['directions'][-1]['file'])
    out = ai.call(studio, pid, 'script', {'idea': st['idea'], 'title': st['title'], 'direction': d, 'research': studio.research(pid)})
    if out.get('unsupported'):
        raise RuntimeError(out['reason'])
    hooks = out['hooks']
    studio.act(pid, 'hooks', {'options': [{k: o[k] for k in ('id', 'type', 'spoken', 'on_screen', 'visual')} | {'pays_off': o.get('pays_off', '')} for o in hooks['options']],
                              'recommended': hooks['recommended'], 'reasons': hooks['reasons'], 'author': 'copilot'}, actor='copilot')
    rec = next(o for o in hooks['options'] if o['id'] == hooks['recommended'])
    studio.act(pid, 'hook_select', {'hook': rec['id'], 'note': 'recommended by the AI writer (not approved)'}, actor='copilot')
    lines = [{'id': 'h', 'text': rec['spoken'], 'role': 'hook'}] + [{'id': l['id'], 'text': l['text']} for l in out['lines'] if l['id'] != 'h']
    r = studio.act(pid, 'script_version', {'lines': lines, 'note': 'Co-Pilot draft (AI writer)' + (' — MOCK AI' if out.get('mock') else ''), 'author': 'copilot'}, actor='copilot')
    v = r['result']['v']
    claims = {l['id']: l.get('claims', []) for l in out['lines']}
    claims['h'] = []
    studio.act(pid, 'cp_script_meta', {'v': v, 'direction_v': direction_v, 'claims': claims, 'texts': {l['id']: l['text'] for l in lines},
                                       'round': 0, 'author': 'ai', 'label': out.get('label'),
                                       'hooks': {o['id']: o.get('pays_off_line') for o in hooks['options']}}, actor='copilot')
    task.unit(what='script')
    return {'v': v}


def _claims_for(cp, v, lines):
    """Claim ids per line, only where the sentence is exactly the one those claims were given for. A line the owner
    rewrote carries no claim ids: the fact checker has to find support for it from scratch."""
    known = {}
    for m in sorted(cp['script_meta'].values(), key=lambda m: m['v']):
        if m['v'] > v: continue
        for lid, ids in (m.get('claims') or {}).items():
            t = (m.get('texts') or {}).get(lid)
            if t is not None: known[lid] = (t, ids)
    return {l['id']: known[l['id']][1] for l in lines if l['id'] in known and known[l['id']][0] == l['text']}


def s_script_check(studio, pid, task, key, v):
    st = studio.state(pid)
    cp = st['copilot']
    sv = next(s for s in st['scripts'] if s['v'] == v)
    lines = studio._version_lines(pid, sv)['lines']
    res = studio.research(pid)
    cl = _claims_for(cp, v, lines)
    hook = next((o for o in st['hooks']['options'] if o['id'] == st['hooks']['selected']), None)
    pays = {}                                            # a hook relies on the claims of the line that pays it off
    for m in cp['script_meta'].values(): pays.update(m.get('hooks') or {})
    hook_claims = cl.get(pays.get(st['hooks']['selected']) or '', [])
    payload = [{'id': l['id'], 'text': l['text'], 'claims': hook_claims if l.get('role') == 'hook' else cl.get(l['id'], [])} for l in lines]
    fc = ai.call(studio, pid, 'fact_check', {'lines': payload, 'research': res})
    task.unit(what='fact check')
    qr = ai.call(studio, pid, 'quality_review', {'lines': payload})
    task.unit(what='editor')
    merged = factcheck.merge(lines, res, sv['checks'], fc)
    for lid, notes in (qr.get('lines') or {}).items():
        if lid not in merged: continue
        m = merged[lid]
        for q in notes:
            m['why'].append(f"editor: {q['detail']}")
            m.setdefault('quality', []).append(q)
            if factcheck.SEV.get(q['severity'], 0) > factcheck.SEV.get(m['severity'], -1) and q['severity'] != 'info':
                m['severity'] = q['severity']
            elif m['severity'] == 'none':
                m['severity'] = q['severity']
    studio.act(pid, 'cp_check', {'id': f'chk-script-{v}', 'target': 'script', 'ref': v, 'kind': 'merged', 'lines': merged,
                                 'by': fc.get('label'), 'fact_label': fc.get('label'), 'quality_label': qr.get('label'),
                                 'keyword': [c for c in sv['checks'] if c['code'] == 'CLAIM_UNSUPPORTED']}, actor='reviewer')
    return {'critical': sum(1 for x in merged.values() if x['severity'] == 'critical')}


def s_script_revise(studio, pid, task, key, v, owner=False, note='', targets=None):
    st = studio.state(pid)
    cp = st['copilot']
    sv = next(s for s in st['scripts'] if s['v'] == v)
    lines = studio._version_lines(pid, sv)['lines']
    mc = merged_check(cp, v) or {'lines': {}}
    meta = script_meta(cp, v) or {'claims': _claims_for(cp, v, lines), 'direction_v': cp['directions'][-1]['v'], 'hooks': {}}
    n_owner = sum(1 for m in cp['script_meta'].values() if m.get('owner_revision'))
    out = ai.call(studio, pid, 'revise_script', {'lines': lines, 'findings': {l: mc['lines'].get(l, {}).get('why', []) for l in (targets or mc['lines'])},
                                                  'targets': targets or [], 'note': note, 'owner': owner, 'owner_round': n_owner})
    ch = {k: t for k, t in (out.get('lines') or {}).items() if any(l['id'] == k and l.get('role') != 'hook' for l in lines)}
    if not ch:
        _done(studio, pid, key, 'script', result='no change')
        if owner:
            studio.act(pid, 'cp_exception', {'id': f'ex-ai-revise-{v}', 'kind': 'ai', 'scene': None, 'title': 'The AI could not make the change you asked for',
                                             'detail': out.get('why', ''), 'detail_ar': 'لم يستطع الذكاء تنفيذ طلبك: عدّل الجملة بنفسك من محرر الجمل',
                                             'options': ['edit_myself', 'manual'], 'pause': True}, actor='copilot')
        return {'changed': 0}
    new = [dict(l, text=ch[l['id']]) if l['id'] in ch else l for l in lines]
    r = studio.act(pid, 'script_version', {'lines': new, 'note': ('revision you asked for: ' if owner else 'self-revision: ') + out.get('why', ''),
                                           'author': 'copilot', 'parent': v}, actor='copilot')
    nv = r['result']['v']
    cl = {**_claims_for(cp, v, lines), **{k: (out.get('claims') or {}).get(k, (meta.get('claims') or {}).get(k, [])) for k in ch}}
    studio.act(pid, 'cp_script_meta', {'v': nv, 'direction_v': meta.get('direction_v'), 'claims': cl, 'texts': {l['id']: l['text'] for l in new},
                                       'hooks': meta.get('hooks', {}),
                                       'round': (meta.get('round', 0) + (0 if owner else 1)), 'author': 'ai', 'owner_revision': owner,
                                       'why': out.get('why', ''), 'label': out.get('label'), 'changed': sorted(ch)}, actor='copilot')
    _done(studio, pid, key, 'script', result=f'v{nv}')
    task.unit(what='revision')
    return {'v': nv}


def s_pron(studio, pid, task, key, v):
    st = studio.state(pid)
    sv = next(s for s in st['scripts'] if s['v'] == v)
    lines = studio._version_lines(pid, sv)['lines']
    out = ai.call(studio, pid, 'pronunciation', {'lines': lines})
    have = {p['word'] for p in st['copilot']['pron']}
    for e in out.get('entries', []):
        if e['word'] in have: continue
        studio.act(pid, 'cp_pron', {'op': 'add', 'word': e['word'], 'respell': e['respell'], 'lines': e.get('lines'), 'why': e.get('why_ar') or e.get('why', '')},
                   actor='copilot')
    _done(studio, pid, key, 'voice', proposals=len(out.get('entries', [])))
    task.unit(what='pronunciation')
    return {}


def s_voice(studio, pid, task, key):
    return V.generate(studio, pid, task)


def s_respell(studio, pid, task, key, lines):
    out = V.generate(studio, pid, task, lines=lines, reason='pronunciation dictionary change')
    _done(studio, pid, key, 'voice', made=out['made'], reused=out['reused'])
    return out


def s_mix(studio, pid, task, key):
    return voicekit.mix(studio, pid, task)


def s_adjust(studio, pid, task, key, adj):
    out = voicekit.adjust(studio, pid, task, adj['line'], adj['take'], adj['speed'], adj['pause_before'], adj['pause_after'])
    _done(studio, pid, key, 'voice', take=out['take'])
    return out


def s_brief(studio, pid, task, key, v):
    st = studio.state(pid)
    sv = next(s for s in st['scripts'] if s['v'] == v)
    out = ai.call(studio, pid, 'art_brief', {'lines': studio._version_lines(pid, sv)['lines']})
    b = {k: x for k, x in out.items() if k not in ('mock', 'label')}
    studio.act(pid, 'art_brief', {'brief': b}, actor='copilot')
    _done(studio, pid, key, 'style', label=out.get('label'))
    task.unit(what='brief')
    return {}


def s_styles(studio, pid, task, key):
    st = studio.state(pid)
    brief = studio.read_json(pid, st['art']['brief'])
    order = FM.order(studio, pid, st)
    hook = next((o for o in st['hooks']['options'] if o['id'] == st['hooks']['selected']), None)
    hv = brief.get('hook_visuals', {}).get(hook['id']) if hook else None
    cp = st['copilot']
    verified = {a['slot']: a for a in cp['assets'].values() if a['status'] == 'verified' and a.get('slot')}
    reg = styles.registry()
    n = len(cp['styles']) + 1
    dirs = []
    for s in reg['styles']:
        d = {k: s.get(k) for k in ('id', 'version', 'name', 'name_ar', 'about_ar', 'status', 'params_hash')}
        d['ready'] = s['status'] == 'ready'
        if s['status'] == 'needs_assets':
            need = [a for a in cp['asset_needs']] or [1]
            d['why_not'] = 'needs licensed photographs for its scenes; the project has ' + str(len(verified))
            d['why_not_ar'] = f'يحتاج صورًا مرخّصة لمشاهده؛ في المشروع {len(verified)} فقط'
        if d['ready']:
            d.update(styles.board(studio, pid, s, brief, order, hv, verified, st['brand'], studio.pdir(pid) / 'work' / f'style-{n}-{s["id"]}'))
        dirs.append(d)
        task.unit(scene=s['id'])
    ev = ai.call(studio, pid, 'style_eval', {'directions': [{k: d.get(k) for k in ('id', 'name', 'ready', 'stills')} for d in dirs]})
    rec = {'n': n, 'brief': st['art']['brief'], 'registry': reg['version'], 'directions': dirs, 'recommended': ev['recommended'],
           'reasons': ev.get('reasons', {}), 'reasons_ar': ev.get('reasons_ar', {}), 'eval_by': ev.get('label')}
    rec['file'] = studio.put(pid, json.dumps(rec, ensure_ascii=False, sort_keys=True).encode(), 'json')
    studio.act(pid, 'cp_style', rec, actor='copilot')
    return {'styles': len(dirs)}


def s_assets(studio, pid, task, key):
    st = studio.state(pid)
    order = FM.order(studio, pid, st)
    out = ai.call(studio, pid, 'asset_search', {'scenes': order})
    cp = st['copilot']
    needs = []
    for nd in out.get('needs', []):
        have = [a for a in cp['assets'].values() if a.get('slot') == nd['id']]
        nd = dict(nd, have=[{'id': a['id'], 'status': a['status']} for a in have],
                  status='verified' if any(a['status'] == 'verified' for a in have) else 'unverified upload' if have else 'missing')
        needs.append(nd)
    studio.act(pid, 'cp_asset_needs', {'needs': needs, 'by': out.get('label')}, actor='copilot')
    _done(studio, pid, key, 'assets', needs=len(needs))
    task.unit(what='assets')
    return {}


def s_rights(studio, pid, task, key, asset):
    a = studio.state(pid)['copilot']['assets'][asset]
    studio.act(pid, 'cp_exception', {'id': f'ex-rights-{asset}', 'kind': 'rights', 'scene': a.get('scene') or None, 'asset': asset,
                                     'title': f'Picture «{a.get("name") or a["id"]}» has no licence evidence',
                                     'detail': 'it will not be used until you add the licence evidence; the scene keeps its fallback',
                                     'detail_ar': 'لن تُستخدم الصورة حتى تضيف دليل الترخيص؛ يبقى البديل في المشهد',
                                     'options': ['keep_fallback'], 'pause': False}, actor='copilot')
    task.unit(what='rights')
    return {}


def s_rights_ok(studio, pid, task, key, asset):
    studio.act(pid, 'cp_exception', {'id': f'ex-rights-{asset}', 'status': 'resolved', 'decision': 'licence evidence added',
                                     'note': 'resolved by the licence evidence you added'}, actor='copilot')
    task.unit(what='rights')
    return {}


def s_task(studio, pid, task, key, task_id):
    st = studio.state(pid)
    t = next(x for x in st['copilot']['tasks'] if x['id'] == task_id)
    tech = None
    if t.get('scene') and st['copilot']['scenes'].get(t['scene'], {}).get('pick'):
        d = st['copilot']['scenes'][t['scene']]
        tech = next(v for v in d['versions'] if v['n'] == d['pick']['n'])['technique']
    out = ai.call(studio, pid, 'comment_to_change', {'text': t['what'], 'scene': t.get('scene'), 'technique': tech})
    ch = {k: str(v) for k, v in (out.get('changes') or {}).items() if k in SC.OWNER_KEYS}
    if t.get('scene') and ch:
        studio.act(pid, 'cp_task', {'id': t['id'], 'status': 'applied', 'changes': ch, 'why': out.get('why', ''), 'by': out.get('label')}, actor='copilot')
    else:
        studio.act(pid, 'cp_task', {'id': t['id'], 'status': 'needs_manual', 'why': out.get('why', 'no scene at that time'), 'by': out.get('label')}, actor='copilot')
        studio.act(pid, 'cp_exception', {'id': f'ex-{t["id"]}', 'kind': 'comment', 'scene': None, 'title': f'Your comment needs a person: «{t["what"][:60]}»',
                                         'detail': out.get('why', ''), 'detail_ar': 'لم يستطع الذكاء تحويل تعليقك إلى تعديل آمن',
                                         'options': ['manual', 'dismiss_comment'], 'pause': False}, actor='copilot')
    task.unit(what='comment')
    return {'changes': ch}


def s_feedback(studio, pid, task, key, gate, note, xid):
    """A rejected style set or film with a free-text note. The Co-Pilot makes only safe parameter changes; a new style
    or a new direction for the film needs a person, so it says so instead of pretending to work on it."""
    what = {'G4': ('A different style needs a person (the style registry): the Co-Pilot can only draw the styles it has',
                   'أسلوب مختلف يحتاج شخصًا (سجل الأساليب): المساعد يرسم الأساليب الموجودة فقط'),
            'G5': ('Your note on the film needs a person. For a change the Co-Pilot can make, add a comment at the moment in the film',
                   'ملاحظتك على الفيلم تحتاج شخصًا. لتعديل يقدر عليه المساعد، أضف تعليقًا عند لحظة معيّنة في الفيلم')}[gate]
    studio.act(pid, 'cp_exception', {'id': xid, 'kind': 'owner_feedback', 'scene': None, 'gate': gate, 'title': what[0] + f' — «{note[:80]}»',
                                     'detail': note, 'detail_ar': what[1], 'options': ['manual', 'dismiss_comment'], 'pause': False}, actor='copilot')
    task.unit(what='feedback')
    return {}


def s_scene(studio, pid, task, key, scene):
    return SC.run(studio, pid, task, scene)


def s_film(studio, pid, task, key):
    out = FM.assemble(studio, pid, task)
    st = studio.state(pid)
    f = next(x for x in st['copilot']['films'] if x['n'] == out['film'])
    for x in st['review']['findings'].values():                       # earlier films' findings: the same checks ran again on this one
        if not x['decision'] and x['run'] not in f['reviews']:
            studio.act(pid, 'finding_decision', {'finding': x['id'], 'decision': 'dismissed',
                                                 'note': f'superseded by film v{f["n"]}: the same checks ran again on it'}, actor='copilot')
    for t in studio.state(pid)['fix_tasks']:
        if t['status'] == 'open':
            studio.act(pid, 'fix_done', {'task': t['id'], 'note': f're-made in film v{f["n"]} and checked again there'}, actor='copilot')
    return out


def s_triage(studio, pid, task, key, n):
    """Safe fixes for what the film review found, at most `max_rounds` films in a row without the owner."""
    st = studio.state(pid)
    cp = st['copilot']
    f = next(x for x in cp['films'] if x['n'] == n)
    auto_films = 0
    for x in reversed(cp['films']):
        if x['n'] >= n: continue
        if any(t.get('film') == x['n'] and t.get('source', '').startswith('finding') for t in cp['tasks']): auto_films += 1
        else: break
    made = 0
    if auto_films < cp['settings'].get('max_rounds', 2):
        for x in st['review']['findings'].values():
            if x['decision'] or x['run'] not in f['reviews'] or not x.get('scene') or x['code'] not in FM.AUTO_FIX: continue
            d = cp['scenes'].get(x['scene'])
            if not d: continue
            tech = next(v for v in d['versions'] if v['n'] == d['pick']['n'])['technique']
            if tech not in ('kinetic_type', 'dark_keynote'): continue
            studio.act(pid, 'finding_decision', {'finding': x['id'], 'decision': 'accepted', 'note': 'the Co-Pilot applies a safe fix'}, actor='copilot')
            tid = f'tk{len(studio.state(pid)["copilot"]["tasks"]) + 1}'
            studio.act(pid, 'cp_task', {'id': tid, 'scene': x['scene'], 'source': f'finding {x["id"]}', 'what': x['recommendation'],
                                        'changes': FM.AUTO_FIX[x['code']], 'status': 'applied', 'film': n}, actor='copilot')
            made += 1
    _done(studio, pid, key, 'film', fixes=made)
    task.unit(what='triage')
    return {'fixes': made}


def s_plan(studio, pid, task, key):
    from ..studio import gate
    rec = gate.plan(studio, pid)
    task.unit(what='plan')
    return {'blockers': len(rec['blockers'])}


# ====================================================================== the runner
_LOCK = threading.Lock()
_RUN: dict[tuple, dict] = {}


def kick(studio, pid):
    """Make sure the Co-Pilot is working on this project if there is free authorized work (idempotent)."""
    if os.environ.get('VD_COPILOT_MANUAL_STEP') == '1':
        return False                                   # tests step the Co-Pilot by hand
    k = (str(studio.var), pid)
    with _LOCK:
        r = _RUN.get(k)
        if r and r['thread'].is_alive():
            r['again'] = True; return False
        r = {'again': False}
        r['thread'] = threading.Thread(target=_loop, args=(studio, pid, r), name=f'copilot-{pid}', daemon=True)
        _RUN[k] = r
        r['thread'].start()
        return True


def running(studio, pid) -> bool:
    r = _RUN.get((str(studio.var), pid))
    return bool(r and r['thread'].is_alive())


def _loop(studio, pid, r):
    while True:
        try:
            st = studio.state(pid)
            cp = st['copilot']
            p = plan(studio, pid, st) if cp['mode'] == 'copilot' and cp['run'] == 'running' else {'step': None, 'waiting': []}
            cur = A.current(st)
            for g in p['waiting']:
                rd = cp['ready'].get(g)
                if cur[g] and (not rd or rd['content_hash'] != cur[g]['hash']):
                    studio.act(pid, 'cp_ready', {'gate': g, 'ref': cur[g]['ref'], 'content_hash': cur[g]['hash']}, actor='copilot')
            s = p['step']
            if s is None:
                with _LOCK:
                    if r['again']:
                        r['again'] = False; continue
                    return
            jobs.start(studio, pid, 'copilot', s.stage, s.what, s.units, s.fn, {'key': s.key, **s.args}, sync=True)
            st = studio.state(pid)
            j = st['jobs'][-1] if st['jobs'] else {}
            if j.get('state') == 'failed':
                with _LOCK:
                    if not r['again']: return
                    r['again'] = False
        except Exception:
            import traceback; traceback.print_exc()
            time.sleep(1)
            with _LOCK:
                if not r['again']: return
                r['again'] = False


def resume_all(studio):
    """After a restart: carry on every Co-Pilot project that was running (interrupted work is redone, not duplicated)."""
    out = []
    for p in studio.projects():
        st = studio.state(p['id'])
        if st['copilot']['mode'] == 'copilot' and st['copilot']['run'] == 'running':
            kick(studio, p['id']); out.append(p['id'])
    return out
