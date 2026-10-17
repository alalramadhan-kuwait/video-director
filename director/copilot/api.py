"""HTTP-facing layer of the Co-Pilot: the guided Studio's view of a project, and the owner's actions.

Every POST is an owner action (the page cannot act as the Co-Pilot, the reviewer or the system). After any recorded
action the Co-Pilot is nudged: an approved gate, a decided exception, a resume, a comment → it carries on by itself
with the free work that is now authorized. Nothing here can reach a paid provider.
"""
from __future__ import annotations
import base64, os, re, signal, time
from datetime import datetime
from pathlib import Path

from ..studio import api as SA
from ..studio.store import Refused
from . import ai, approvals as A, orchestrator as O, scenes as SC, styles
from .voicekit import effective_takes

OWNER_ACTIONS = {'cp_mode', 'cp_settings', 'cp_control', 'cp_ai_budget', 'cp_gate', 'cp_hook', 'cp_line_edit', 'cp_pron',
                 'cp_voice_adjust', 'cp_asset', 'cp_exception_decision', 'cp_comment', 'cp_finding'}
MAX_UPLOAD = 12 * 1024 * 1024
IMAGE_EXT = {'jpg', 'jpeg', 'png', 'webp'}


def studio(var):
    return SA.studio(var)


def _url(pid, rel):
    return f'/files/{pid}/{rel}' if rel else None


def _ts(s):
    try: return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    except Exception: return None


def kill_renders(S, pid):
    out = []
    for pf in (S.pdir(pid) / 'work').glob('**/render.pid'):
        try:
            p = int(pf.read_text().strip())
            if 'render.mjs' in Path(f'/proc/{p}/cmdline').read_bytes().decode(errors='replace'):
                os.killpg(p, signal.SIGTERM); out.append(p)
        except (ValueError, OSError):
            pass
    return out


# ====================================================================== actions
def handle(var, body: dict) -> tuple[int, dict]:
    S = studio(var)
    pid, action, args, rid = body.get('project'), body.get('action', ''), dict(body.get('args') or {}), body.get('request_id')
    try:
        if action == 'create':
            mode = args.get('mode', 'copilot')
            if mode == 'auto': raise Refused('Auto mode is not yet implemented')
            r = S.act(None, 'create_project', {k: args.get(k) for k in ('title', 'idea', 'brand')}, 'owner', rid)
            if r['status'] == 'duplicate':
                return 200, r
            pid = r['project']
            S.act(pid, 'cp_mode', {'mode': mode, 'note': 'chosen when the project was created'}, 'owner', (rid or pid) + '-mode')
            st = {k: args[k] for k in ('duration_s', 'format') if args.get(k)}
            if st: S.act(pid, 'cp_settings', st, 'owner', (rid or pid) + '-set')
            prof = S.profile(args['brand'])
            dv = next(iter((prof.get('voice') or {}).get('voices') or {}), None)
            if dv: S.act(pid, 'set_voice', {'voice': dv}, 'owner', (rid or pid) + '-voice')
            if mode == 'copilot': O.kick(S, pid)
            return 200, {'status': 'recorded', 'project': pid, 'mode': mode}
        if action == 'upload':
            data = base64.b64decode(args.pop('data', '') or '', validate=False)
            ext = (args.pop('ext', '') or Path(args.get('name', '')).suffix.lstrip('.')).lower()
            if not data: raise Refused('the file is empty')
            if len(data) > MAX_UPLOAD: raise Refused('the file is larger than 12 MB')
            if ext not in IMAGE_EXT: raise Refused('upload a JPG, PNG or WebP picture')
            rel = S.put(pid, data, 'jpg' if ext == 'jpeg' else ext)
            r = S.act(pid, 'cp_asset', {**args, 'op': 'add', 'file': rel}, 'owner', rid)
            O.kick(S, pid)
            return 200, r
        if action not in OWNER_ACTIONS:
            raise Refused(f'{action} cannot be sent from the page')
        r = S.act(pid, action, args, 'owner', rid)
        if r['status'] == 'recorded':
            if action == 'cp_control' and args.get('op') == 'stop':
                r['stopped_renders'] = kill_renders(S, pid)
            if action == 'cp_exception_decision' and args.get('decision') == 'manual':
                S.act(pid, 'cp_mode', {'mode': 'manual', 'note': 'chosen from an exception'}, 'owner', (rid or 'x') + '-manual')
            O.kick(S, pid)
        return 200, r
    except Refused as e:
        S.refuse_log(pid, action, {k: v for k, v in args.items() if k != 'data'}, str(e), 'owner')
        return 422, {'status': 'refused', 'reason': str(e), 'action': action}


# ====================================================================== the view
def projects(var):
    S = studio(var)
    out = []
    for p in S.projects():
        st = S.state(p['id'])
        cp = st['copilot']
        out.append({**p, 'mode': cp['mode'] or 'classic', 'run': cp['run'], 'films': len([f for f in cp['films'] if f.get('state') == 'ok'])})
    return out


def _timing(st, now, waiting=()):
    cp = st['copilot']
    proc, by_stage = 0.0, {}
    for j in st['jobs']:
        if j.get('kind') != 'copilot': continue
        s = j.get('seconds')
        if j['state'] == 'running':
            s = max(0.0, now - (_ts(j['at']) or now))
        if s:
            proc += s; by_stage[j['stage']] = by_stage.get(j['stage'], 0) + s
    wait, by_gate, waiting_now = 0.0, {}, None
    for g in A.GATES:
        readies = [c for c in st['history'] if c['action'] == 'cp_ready' and c['summary'].startswith(g)]
        decs = [r for r in cp['gates'][g]]
        for rd in readies:
            t0 = _ts(rd['at'])
            nxt = next((d for d in decs if d['at'] >= rd['at']), None)
            t1 = _ts(nxt['at']) if nxt else None
            if t1 is None:
                cur = A.current(st)[g]
                if cur and cp['ready'].get(g, {}).get('content_hash') == cur['hash'] and g in waiting:     # includes a replacement waiting for review
                    t1 = now; waiting_now = waiting_now or {'gate': g, 'since': rd['at']}
                else:
                    continue
            by_gate[g] = by_gate.get(g, 0) + max(0, t1 - t0); wait += max(0, t1 - t0)
    return {'processing_s': round(proc, 1), 'processing_by_stage': {k: round(v, 1) for k, v in by_stage.items()},
            'waiting_s': round(wait, 1), 'waiting_by_gate': {k: round(v, 1) for k, v in by_gate.items()}, 'waiting_now': waiting_now,
            'note': 'processing = time the Co-Pilot worked; waiting = time a decision waited for you. No finish time is guessed.'}


def view(var, pid) -> dict:
    S = studio(var)
    st = S.state(pid)
    cp = st['copilot']
    now = time.time()
    val = A.validity(st)
    cur = A.current(st)
    p = O.plan(S, pid, st)
    runs = S.log.runs(pid)
    live = [j for j in st['jobs'] if j.get('kind') == 'copilot' and j['state'] == 'running']
    task = None
    if live:
        j = live[-1]
        r = next((x for x in reversed(runs) if x['task'] == j['what'] and x['state'] == 'running'), None)
        sub = next((x for x in reversed(runs) if x['state'] == 'running' and x['task'] != j['what']), None)
        task = {'what': j['what'], 'stage': j['stage'], 'since': j['at'], 'elapsed_s': round(now - (_ts(j['at']) or now), 1),
                'units_done': r and r['units_done'], 'units_total': r and r['units_total'],
                'eta_s': (sub or r or {}).get('eta_s'), 'eta_reason': (sub or r or {}).get('eta_reason'), 'sub': sub and {'task': sub['task'], 'units': f"{sub['units_done']}/{sub['units_total']}"},
                'interrupted': j['id'] not in S.jobs}
    stuck = [j for j in st['jobs'] if j.get('kind') == 'copilot' and j['state'] == 'interrupted']
    ex_open = [x for x in cp['exceptions'] if x['status'] == 'open']
    # ---------------------------------------------------------------- stages
    stage_rows = []
    for sid, g, en, ar in O.STAGES:
        state, why = 'not_started', ''
        working = task and task['stage'] == sid
        blocked = [b for b in p['blocked'] if b['stage'] == sid]
        if g:
            last = A.last(cp, g)
            if val[g]['valid']: state = 'owner_approved'
            elif working: state = 'working'
            elif blocked: state, why = 'blocked', blocked[0]['error']
            elif g in p['waiting']: state = 'needs_owner'
            elif cur[g] and last and last['content_hash'] == cur[g]['hash'] and last['decision'] != 'approved': state = 'changes_requested'
            elif val[g]['approved']: state, why = 'outdated', val[g]['why'] or ''
            elif cur[g]: state = 'ai_review'
            if g == 'G6' and st['gate']['plan'] and not val['G6']['valid']:
                state, why = 'blocked', 'paid narration is locked in this workspace'
        elif sid == 'assets':
            rights = [x for x in ex_open if x['kind'] == 'rights']
            state = 'working' if working else 'needs_owner' if rights else 'completed' if cp['asset_needs'] or any(s.get('key', '').startswith('assets:') for s in cp['stages']) else 'not_started'
        elif sid == 'scenes':
            sc = p.get('scenes') or {}
            if working: state = 'working'
            elif any(x.get('scene') for x in ex_open): state = 'needs_owner'
            elif sc and all(sc.values()): state = 'completed'
            elif any(cp['scenes'].get(s, {}).get('pick') for s in sc): state = 'outdated' if not working else 'working'
        elif sid == 'export':
            state, why = 'blocked', 'needs the paid narration, then a master approval; publishing is a separate authorization (never automatic)'
        stage_rows.append({'id': sid, 'gate': g, 'name': en, 'name_ar': ar, 'state': state, 'why': why,
                           'state_name': A.STATE_NAME[state][0], 'state_name_ar': A.STATE_NAME[state][1]})
    first = next((s for s in stage_rows if s['state'] not in ('owner_approved', 'completed')), stage_rows[-1])
    nxt = None
    if ex_open:
        nxt = {'kind': 'exception', 'id': ex_open[0]['id'], 'title': ex_open[0]['title'], 'title_ar': ex_open[0].get('detail_ar', '')}
    for g in p['waiting']:
        if nxt is None and not (g == 'G6'):
            nxt = {'kind': 'gate', 'gate': g, 'title': A.GATE_NAME[g][0], 'title_ar': A.GATE_NAME[g][1]}
    top = {'project': st['title'], 'stage': first['name'], 'stage_ar': first['name_ar'], 'stage_id': first['id'],
           'task': task['what'] if task else ('paused' if cp['run'] == 'paused' else 'stopped' if cp['run'] == 'stopped' else
                                              'waiting for you' if nxt else 'nothing running'),
           'next': nxt}
    out = {'id': pid, 'title': st['title'], 'idea': st['idea'], 'brand': st['brand'], 'mode': cp['mode'] or 'classic', 'run': cp['run'],
           'paused_by': cp.get('paused_by'), 'settings': cp['settings'], 'top': top, 'stages': stage_rows, 'task': task,
           'interrupted': [{'what': j['what'], 'at': j['at']} for j in stuck], 'blocked': p['blocked'], 'waiting': p['waiting'],
           'runner_alive': O.running(S, pid), 'validity': {g: {'valid': v['valid'], 'why': v['why']} for g, v in val.items()},
           'current': {g: (c and {'ref': c['ref'], 'hash': c['hash']}) for g, c in cur.items()},
           'gates': {g: [{k: r.get(k) for k in ('decision', 'ref', 'note', 'at', 'by', 'content_hash')} for r in cp['gates'][g]] for g in A.GATES},
           'exceptions': [{k: x.get(k) for k in ('id', 'kind', 'scene', 'title', 'detail', 'detail_ar', 'options', 'status', 'decision', 'decision_note', 'at', 'asset')}
                          | {'evidence': [_url(pid, e) for e in x.get('evidence') or []]} for x in cp['exceptions']],
           'timing': _timing(st, now, p['waiting']), 'classic_url': f'/studio/classic#{pid}'}
    out['ai'] = {'worker': cp['settings'].get('worker', 'mock'), 'label': ai.MOCK_LABEL if cp['settings'].get('worker', 'mock') == 'mock' else ai.CLAUDE_LABEL,
                 'budget_usd': cp['ai']['budget_usd'], 'spent_usd': cp['ai']['spent_usd'], 'real_enabled': os.environ.get('VD_AI_REAL_ENABLED') == '1',
                 'calls': [{k: c.get(k) for k in ('kind', 'role', 'worker', 'ok', 'cost_usd', 'duration_s', 'at', 'error', 'model')} for c in cp['ai']['calls'][-40:]],
                 'n_calls': len(cp['ai']['calls'])}
    out['cost_lock'] = {'paid_enabled': os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') == '1', 'paid_spent': 0,
                        'text': 'Paid narration, paid images and paid video are locked in this workspace. Nothing is generated or spent automatically.',
                        'text_ar': 'التعليق المدفوع والصور والفيديو المدفوعة مقفلة هنا. لا يُنفق شيء تلقائيًا.'}
    out['g1'] = _g1(S, pid, st, cp)
    out['g2'] = _g2(S, pid, st, cp)
    out['g3'] = _g3(S, pid, st, cp)
    out['g4'] = _g4(S, pid, st, cp)
    out['assets'] = _assets(S, pid, st, cp)
    out['scenes'] = _scenes(S, pid, st, cp, p)
    out['g5'] = _g5(S, pid, st, cp)
    out['g6'] = _g6(S, pid, st, cp, val)
    out['inbox'] = _inbox(out)
    out['history'] = [{k: h[k] for k in ('at', 'actor', 'action', 'summary')} for h in st['history'][-80:]][::-1]
    return out


def _g1(S, pid, st, cp):
    if not cp['directions']: return None
    d = cp['directions'][-1]
    doc = S.read_json(pid, d['file'])
    res = S.research(pid) or {}
    chk = next((c for c in reversed(cp['checks']) if c['target'] == 'direction' and c['ref'] == d['v']), None)
    return {'v': d['v'], 'doc': doc, 'label': d.get('label'), 'mock': d.get('mock'), 'claims': res.get('claims', []), 'terms': res.get('terms', []),
            'verdict': res.get('verdict'), 'check': chk and {'findings': chk['findings'], 'by': chk.get('by')}, 'versions': len(cp['directions'])}


def _g2(S, pid, st, cp):
    if not st['scripts']: return None
    sv = st['scripts'][-1]
    lines = S._version_lines(pid, sv)['lines']
    mc = next((c for c in reversed(cp['checks']) if c['target'] == 'script' and c['ref'] == sv['v'] and c['kind'] == 'merged'), None)
    hk = st['hooks']
    meta = O.script_meta(cp, sv['v'])
    ap = [s for s in st['scripts'] if s['status'] == 'approved']
    return {'v': sv['v'], 'status': sv['status'], 'author': sv['author'], 'note': sv['note'], 'lines': lines,
            'check': mc and {'lines': mc['lines'], 'fact_label': mc.get('fact_label'), 'quality_label': mc.get('quality_label'), 'keyword': mc.get('keyword')},
            'keyword_checks': sv['checks'], 'diff': sv['diff'], 'meta': meta,
            'versions': [{k: s.get(k) for k in ('v', 'status', 'author', 'note', 'at', 'parent')} for s in st['scripts']],
            'approved_v': ap[-1]['v'] if ap else None,
            'hooks': {'options': hk['options'], 'recommended': hk['recommended'], 'reasons': hk['reasons'], 'selected': hk['selected'],
                      'pays_off': (meta or {}).get('hooks', {})}}


def _g3(S, pid, st, cp):
    vl = st['voice'].get('lines') or {}
    if not vl: return None
    mix = cp['voice_mix']
    lines = []
    for lid, x in vl.items():
        takes = []
        for tid in st['voice']['by_line'].get(lid, []):
            t = st['voice']['takes'][tid]
            if t['text'] != x['text']: continue
            takes.append({'id': tid, 'status': t['status'], 'seconds': t['seconds'], 'audio': _url(pid, t['audio']), 'label': t.get('label'),
                          'reason': t.get('reason'), 'processed': t.get('processed'), 'same_audio_as': t.get('same_audio_as'),
                          'words': [{'w': w['w'], 's': w['s'], 'e': w['e'], 'est': bool(w.get('est'))} for w in t['words']], 'spoken': t.get('spoken')})
        lines.append({'line': lid, 'text': x['text'], 'status': x['status'], 'take': x['take'], 'takes': takes})
    tk = st['voice']['takes']
    segs = [dict(x, status=tk[x['take']]['status']) for x in mix['segments']] if mix else []     # decisions made after the mix was built
    return {'mix': mix and {**{k: mix[k] for k in ('seconds', 'takes', 'label', 'file')}, 'segments': segs, 'url': _url(pid, mix['file'])},
            'mix_current': bool(mix) and mix['takes'] == effective_takes(st),
            'pending': [k for k, x in effective_takes(st).items() if x and st['voice']['takes'][x]['status'] != 'approved'],
            'lines': lines, 'pron': cp['pron'], 'qa': cp['voice_qa'], 'adjust': cp['adjust'],
            'label': 'Draft voice: Google text-to-speech (free). Not the final ElevenLabs voice.',
            'label_ar': 'صوت تجريبي مجاني (Google). ليس الصوت النهائي من ElevenLabs.'}


def _g4(S, pid, st, cp):
    if not cp['styles']: return None
    s = cp['styles'][-1]
    ap = A.last(cp, 'G4', 'approved')
    return {'n': s['n'], 'recommended': s['recommended'], 'reasons': s['reasons'], 'reasons_ar': s.get('reasons_ar', {}), 'eval_by': s.get('eval_by'),
            'directions': [{**{k: d.get(k) for k in ('id', 'version', 'name', 'name_ar', 'about_ar', 'ready', 'why_not', 'why_not_ar', 'scenes', 'status')},
                            'board': _url(pid, d.get('board')), 'stills': [_url(pid, x) for x in d.get('stills', [])]} for d in s['directions']],
            'approved': ap and ap.get('style')}


def _assets(S, pid, st, cp):
    return {'needs': cp['asset_needs'],
            'library': [{**{k: a.get(k) for k in ('id', 'slot', 'scene', 'name', 'credit', 'use', 'source', 'status', 'licence', 'url', 'what', 'at')},
                         'file': _url(pid, a.get('file'))} for a in cp['assets'].values()],
            'rule': 'A picture is used only with licence evidence (a page or document that states the licence) or your own declaration that you own it. Genuine historical photographs are never generated.',
            'rule_ar': 'لا تُستخدم صورة إلا بدليل ترخيص أو بإقرارك أنك تملكها. لا تُصنع صور تاريخية أبدًا.'}


def _scenes(S, pid, st, cp, p):
    from ..studio.voice import approved_script
    sv = approved_script(st)
    if not sv: return []
    out = []
    valid = p.get('scenes') or {}
    for ln in S.read_json(pid, sv['file'])['lines']:
        d = cp['scenes'].get(ln['id']) or {'versions': [], 'pick': None}
        pk = d['pick']
        v = next((x for x in d['versions'] if pk and x['n'] == pk['n']), None)
        ex = next((x for x in cp['exceptions'] if x.get('scene') == ln['id'] and x['status'] == 'open'), None)
        state = ('needs_owner' if ex else 'ai_reviewed' if valid.get(ln['id']) else 'outdated' if pk else 'not_started')
        out.append({'id': ln['id'], 'text': ln['text'], 'state': state, 'exception': ex and ex['id'],
                    'pick': v and {'n': v['n'], 'status': pk['status'], 'rounds': pk['rounds'], 'open': pk['open'], 'why': pk['why'],
                                   'technique': v['technique'], 'theme': v['theme'], 'fallback': v.get('fallback'), 'dur': v['dur'],
                                   'stills': [_url(pid, s) for s in v['stills']], 'clip': _url(pid, v['clip']), 'clip_webm': _url(pid, v['clip_webm']),
                                   'reviewer': v.get('reviewer')},
                    'versions': [{'n': x['n'], 'round': x['round'], 'changes': x['changes'], 'score': x['score'], 'still': _url(pid, x['stills'][1]), 'inputs': x['inputs_hash'],
                                  'findings': [{k: f.get(k) for k in ('code', 'severity', 'detail', 'detail_ar', 'by')} for f in x['findings']]} for x in d['versions']]})
    return out


def _g5(S, pid, st, cp):
    films = [f for f in cp['films'] if f.get('state') == 'ok']
    if not films and not cp['films']: return None
    f = films[-1] if films else None
    out = {'films': [{k: x.get(k) for k in ('n', 'state', 'seconds', 'at', 'error')} for x in cp['films']]}
    if not f: return out
    fs = [x for x in st['review']['findings'].values() if x['run'] in f['reviews']]
    sev = {'critical': 0, 'major': 1, 'minor': 2, 'info': 3}
    ap = A.last(cp, 'G5', 'approved')
    prev = next((x for x in films if ap and x['n'] == ap['ref']), None)
    out.update({'n': f['n'], 'seconds': f['seconds'], 'mp4': _url(pid, f['render_file']), 'webm': _url(pid, f.get('preview')), 'poster': _url(pid, f.get('poster')),
                'timeline': f['timeline'], 'label': f.get('label'), 'label_ar': f.get('label_ar'), 'scenes': f['scenes'],
                'findings': sorted([{**{k: x.get(k) for k in ('id', 'code', 'severity', 'detail', 'detail_ar', 'recommendation', 'scene', 't', 'perspective', 'decision', 'decision_note', 'label')},
                                     'evidence': _url(pid, x.get('evidence'))} for x in fs], key=lambda x: (sev.get(x['severity'], 9), x['t'] or 0)),
                'comments': [c for c in cp['comments'] if c['film'] == f['n']], 'tasks': cp['tasks'],
                'approved_film': prev and {'n': prev['n'], 'mp4': _url(pid, prev['render_file']), 'webm': _url(pid, prev.get('preview'))}})
    return out


def _g6(S, pid, st, cp, val):
    g = st['gate']['plan']
    if not g: return {'plan': None, 'locked': True}
    return {'plan': {k: g.get(k) for k in ('hash', 'created', 'script_v', 'voice', 'voice_status', 'voice_why', 'items', 'chars_total', 'blockers',
                                           'budget_remaining', 'paid_enabled', 'proposed_terms', 'overrides')},
            'locked': not (os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') == '1'), 'stale': SA._plan_stale(st),
            'authorized': st['gate'].get('authorized'), 'attempts': st['gate']['attempts'][-5:],
            'note': 'Approval here is single-use, tied to this exact plan, and expires if anything changes. No paid retry is ever automatic.',
            'note_ar': 'الموافقة هنا لمرة واحدة، مرتبطة بهذه الخطة بالضبط، وتسقط عند أي تغيير. لا إعادة مدفوعة تلقائية أبدًا.'}


def _inbox(v):
    G = []
    for x in v['exceptions']:
        if x['status'] == 'open':
            G.append({'group': 'decisions', 'kind': 'exception', 'id': x['id'], 'title': x['title'], 'title_ar': x.get('detail_ar', ''), 'scene': x.get('scene')})
    for g in v['waiting']:
        G.append({'group': 'gates', 'kind': 'gate', 'gate': g, 'title': A.GATE_NAME[g][0], 'title_ar': A.GATE_NAME[g][1]})
    for b in v['blocked']:
        G.append({'group': 'problems', 'kind': 'blocked', 'key': b['key'], 'title': f"{b['what']} failed", 'title_ar': 'خطوة فشلت: ' + b['what'], 'error': b['error']})
    for s in v['scenes']:
        if s['state'] == 'needs_owner':
            G.append({'group': 'scenes', 'kind': 'scene', 'scene': s['id'], 'title': f"Scene {s['id']} needs you", 'title_ar': f"المشهد {s['id']} يحتاجك"})
    return G
