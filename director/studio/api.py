"""HTTP-facing layer of the studio: one POST for every action, background jobs for long work, a state read that also
carries what the progress dashboard needs (current stage, tasks with measured times, ETA only when measured,
blockers, pending approvals, inbox counts, timeline). No route reaches the paid gateway."""
from __future__ import annotations
import os
from pathlib import Path

from ..events import summarize
from . import art, gate, jobs, review, storyboard, voice
from .store import Studio, Refused, FLAG_KINDS, VFLAG_KINDS, STAGE_NAMES

_STUDIOS: dict[str, Studio] = {}


def studio(var) -> Studio:
    k = str(Path(var).resolve())
    if k not in _STUDIOS:
        _STUDIOS[k] = Studio(Path(var))
    return _STUDIOS[k]


JOBS = {  # action -> (kind, stage, what, units(state, args), function, args(state, args))
    'run_voice': ('voice', 'voice', 'draft voice (gTTS, free)', lambda S, st, a: len(_todo_lines(S, st, a)), voice.generate,
                  lambda st, a: {'lines': a.get('lines')}),
    'run_concepts': ('art', 'art', 'art concepts', lambda S, st, a: len(art.brief_for(S, st['id'], st)['scenes'][a['scene']]['concepts']),
                     art.concepts, lambda st, a: {'scene': a['scene']}),
    'run_render': ('render', 'draft', 'draft render (local engine)', lambda S, st, a: 5, storyboard.render, lambda st, a: {}),
}


def _todo_lines(S, st, a):
    nar = voice.narration(S, st['id'], st)
    return [l for l in nar['lines'] if (not a.get('lines') and l['id'] not in st['voice']['by_line']) or (a.get('lines') and l['id'] in a['lines'])] or [0]


def handle(var, body: dict) -> tuple[int, dict]:
    S = studio(var)
    pid, action, args = body.get('project'), body.get('action', ''), body.get('args') or {}
    rid, actor = body.get('request_id'), body.get('actor', 'owner')
    try:
        if action in JOBS:
            # a repeated request (double tap, refresh) must not start the job twice
            if rid and any(e['data'].get('request_id') == rid for e in S.events(pid)):
                return 200, {'status': 'duplicate'}
            st = S.state(pid)
            kind, stage, what, units, fn, fargs = JOBS[action]
            jid = jobs.start(S, pid, kind, stage, what, units(S, st, args), fn, fargs(st, args), request_id=rid)
            return 202, {'status': 'started', 'job': jid}
        if action == 'voice_fix':
            r = S.act(pid, 'voice_fix', args, actor, rid)
            if r['status'] == 'recorded':
                f = r['result']
                r['job'] = jobs.start(S, pid, 'voice', 'voice', f'new take {f["line"]} after a fix', 1, voice.fix_line, {'line': f['line'], 'vflag': f['vflag']})
            return 200, r
        if action == 'art_modify':
            r = S.act(pid, 'art_modify', args, actor, rid)
            if r['status'] == 'recorded' and not r['result'].get('needs_operator'):
                r['job'] = jobs.start(S, pid, 'art', 'art', f'revision of {args["concept"]}', 1, art.revise, {'concept': args['concept']})
            return 200, r
        if action == 'art_operator_revision':
            r = S.act(pid, 'art_operator_revision', args, actor, rid)
            if r['status'] == 'recorded':
                x = r['result']
                r['job'] = jobs.start(S, pid, 'art', 'art', f'revision of {x["concept"]}', 1, art.revise,
                                      {'concept': x['concept'], 'params': x['params'], 'theme': x['theme']})
            return 200, r
        if action == 'run_hook_stills':
            return 202, {'status': 'started', 'job': jobs.start(S, pid, 'hookstills', 'hook', 'hook opening frames', len(S.state(pid)['hooks']['options']), hook_stills)}
        if action == 'run_review':
            st = S.state(pid)
            rnd = args.get('render') or next((r['id'] for r in reversed(st['renders']) if r.get('state') == 'ok'), None)
            if not rnd: raise Refused('render a draft first')
            prof = S.profile(st['brand']); others = [S.profile(b) for b in ('timekeeper', 'diabetes-history') if b != st['brand']]
            return 202, {'status': 'started', 'job': jobs.start(S, pid, 'review', 'review', 'independent review', 7, review.run,
                                                                 {'render_id': rnd, 'profile': prof, 'other_profiles': others, 'research': S.research(pid),
                                                                  'label': args.get('label', 'draft')})}
        if action == 'build_storyboard':
            return 200, {'status': 'recorded', 'result': storyboard.build(S, pid)}
        if action == 'run_gate_plan':
            return 200, {'status': 'recorded', 'result': {k: v for k, v in gate.plan(S, pid).items() if k != 'plan'}}
        if action == 'resume':
            st = S.state(pid)
            j = next((x for x in st['jobs'] if x['id'] == args.get('job')), None)
            if not j or j['state'] not in ('interrupted', 'failed'):
                raise Refused('nothing to resume')
            back = {'voice': 'run_voice', 'art': 'run_concepts', 'render': 'run_render'}.get(j['kind'])
            if j['kind'] == 'review': back = 'run_review'
            if j['kind'] == 'hookstills': back = 'run_hook_stills'
            if not back: raise Refused('this job cannot be resumed; start it again from its step')
            return handle(var, {'project': pid, 'action': back, 'args': j.get('args') or {}, 'actor': actor})
        if action.startswith('run_') or action in ('job', 'voice_take', 'art_concepts', 'art_revision', 'storyboard', 'render', 'review',
                                                    'gate_plan', 'hook_still'):
            raise Refused(f'{action} is recorded by the system, not sent from the page')
        r = S.act(pid, action, args, actor, rid)
        return 200, r
    except Refused as e:
        S.refuse_log(pid, action, args, str(e), actor)
        return 422, {'status': 'refused', 'reason': str(e), 'action': action}


STALE_PLAN = 'the final-voice plan is out of date: rebuild it (Final voice) to see what still blocks paid narration'


def _plan_stale(st) -> bool:
    """Anything recorded after the plan was built (a decision, a take, a render, a review, an art change…) can change
    what it says, so its blockers are not shown as current."""
    g = st['gate']['plan']
    apv = [x for x in st['scripts'] if x['status'] == 'approved']
    return bool((st['voice_profile'] or {}).get('name') != g['voice']['name'] or (apv and apv[-1]['v'] != g['script_v']) or
                g.get('created', '') < max((h['at'] for h in st['history'] if h['action'] not in ('gate_plan', 'hook_still')
                                            and not h['action'].startswith('cp_')), default=''))      # Co-Pilot bookkeeping is not a change


def _take_note(t) -> str:
    """What a new take is, said plainly: a take made after a fix is not 'corrected' until someone hears that it is."""
    if t.get('same_audio_as'): return ' (new take: sounds the same as before — the fix had no effect)'
    if (t.get('reason') or '').startswith('correction'): return ' (new take after a fix — listen to the word)'
    if t.get('processed'): return ' (speed/pauses processed locally)'
    return ''


def _undecided_latest(st, concept, v):
    c = st['art']['concepts'].get(concept)
    return bool(c) and c['versions'][-1]['v'] == v and not c['versions'][-1].get('status')


def hook_stills(S, pid, task):
    st = S.state(pid)
    brief = art.brief_for(S, pid, st)
    for o in st['hooks']['options']:
        hv = brief['hook_visuals'].get(o['id'])
        if not hv: continue
        sc = art.scene_visual(hv['technique'], hv['params'], hv['theme'], 4.5, o['on_screen'])
        sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style(st['brand']), 'scenes': [{**sc, 'dur': 4.5}]}
        from . import engine
        files = engine.stills(sb, S.pdir(pid) / 'work' / f'hook-{o["id"]}', [0.0, 0.5, 2.0], scale=0.6)
        S.act(pid, 'hook_still', {'hook': o['id'], 'still': [S.put_file(pid, f, 'png') for f in files]}, actor='system')
        task.unit(scene=o['id'])
    return {}


def view(var, pid) -> dict:
    """The project as the page shows it (state + progress dashboard)."""
    S = studio(var)
    st = S.state(pid)
    runs = S.log.runs(pid)
    live = {(j['stage'], j['what']) for j in st['jobs'] if j['state'] == 'running'}
    if any(j['kind'] == 'render' for j in st['jobs'] if j['state'] == 'running'):
        live.add(('draft', 'draft frames (10 % steps)'))
    for r in runs:                       # a run the log still calls running but no live job owns died with the server
        if r['state'] == 'running' and (r['stage'], r['task']) not in live:
            r.update(state='interrupted', eta_s=None, eta_reason='interrupted: the server stopped while it ran')
    import time as _t
    from datetime import datetime as _dt
    for r in runs:                       # a running task's elapsed time is the wall clock since it started, not the last unit
        if r['state'] == 'running':
            try: r['elapsed_s'] = round(_t.time() - _dt.fromisoformat(r['started'].replace('Z', '+00:00')).timestamp(), 1)
            except ValueError: pass
    st['runs'] = [r for r in runs][-30:]
    st['running'] = [r for r in runs if r['state'] == 'running']
    pend = []
    for s in st['scripts']:
        if s['status'] == 'draft' and s is st['scripts'][-1]: pend.append({'what': f'Approve script v{s["v"]}', 'step': 'script'})
    if st['research'] and st['research']['status'] == 'waiting': pend.append({'what': 'Approve research', 'step': 'research'})
    if st['hooks']['options'] and not st['hooks']['selected']: pend.append({'what': 'Choose a hook', 'step': 'hook'})
    tk = st['voice']['takes']
    for ln, x in (st['voice'].get('lines') or {}).items():
        if x['status'] == 'candidate': pend.append({'what': f'Listen to line {ln}', 'step': 'voice', 'take': x['take']})
    for sc, ids in st['art']['by_scene'].items():
        if sc not in st['art']['approved']: pend.append({'what': f'Approve art for {sc}', 'step': 'art', 'scene': sc})
    for r in st['renders']:
        if r.get('state') == 'ok' and not r.get('decision'): pend.append({'what': f'Watch draft {r["id"]}', 'step': 'draft'})
    for f in st['review']['findings'].values():
        if not f['decision']: pend.append({'what': f'Decide on finding {f["id"]}', 'step': 'review'})
    st['pending'] = pend
    # ONE inbox: every outstanding decision, grouped, each with where to act
    G = []
    def grp(key, title, step, items):
        if items: G.append({'key': key, 'title': title, 'step': step, 'items': items})
    latest = st['scripts'][-1] if st['scripts'] else None
    grp('research', 'Research to approve', 'research', [{'what': 'Approve the sourced claims', 'href': 'research'}] if st['research'] and st['research']['status'] == 'waiting' else [])
    grp('script', 'Script', 'script', ([{'what': f'Approve or reject script v{latest["v"]}', 'href': f'script/{latest["v"]}'}] if latest and latest['status'] == 'draft' else [])
        + [{'what': f'Correction «{f["word"]}» in {f["line"]} ({FLAG_KINDS[f["kind"]]})', 'href': f'script/{f["v"]}'} for f in st['flags'] if f['status'] == 'open'])
    hk = st['hooks']
    grp('hook', 'Hook', 'hook', ([{'what': 'Choose one of the hooks', 'href': 'hook'}] if hk['options'] and not hk['selected'] else [])
        + ([{'what': f'Confirm the film delivers on {hk["selected"]}', 'href': 'hook'}] if hk['selected'] and not hk['delivery'] else []))
    VL = st['voice'].get('lines') or {}
    grp('voice', 'Draft voice', 'voice', [{'what': f'Re-record {ln}: the script changed after it was voiced' if x['status'] == 'stale' else f'Record {ln}', 'href': 'voice'}
                                         for ln, x in VL.items() if x['status'] in ('stale', 'missing') and st['voice']['takes']]
        + [{'what': f'Listen to {ln}' + _take_note(tk.get(x['take']) or {}), 'href': f'voice/{ln}'}
           for ln, x in VL.items() if x['status'] == 'candidate']
        + [{'what': f'Pronunciation «{f["word"]}» in {f["line"]}: apply the fix', 'href': f'voice/{f["line"]}'} for f in st['voice']['flags'] if f['status'] == 'open']
        + [{'what': f'«{f["word"]}» in {f["line"]}: the draft voice ignored the respelling — try another', 'href': f'voice/{f["line"]}'} for f in st['voice']['flags'] if f['status'] == 'fix_no_effect'])
    grp('art', 'Art', 'art', [{'what': f'Scene {sc}: ' + ('approve the selected concept' if st['art']['selected'].get(sc) else 'choose a concept'), 'href': 'art'}
                             for sc in st['art']['by_scene'] if sc not in st['art']['approved']]
        + [{'what': f'Revision of {q["concept"]} is being drawn', 'href': 'art', 'wait': True} for q in st['art']['requests'] if q['status'] == 'open']
        + [{'what': f'{q["concept"]}: your note is waiting for the art operator', 'href': 'art', 'wait': True} for q in st['art']['requests'] if q['status'] == 'waiting_operator']
        + [{'what': f'{q["concept"]} v{q.get("version")}: the change made no visible difference', 'href': 'art'} for q in st['art']['requests']
           if q['status'] == 'no_visible_change' and _undecided_latest(st, q['concept'], q.get('version'))]
        + [{'what': f'{c["id"]}: approve or reject v{c["versions"][-1]["v"]} (v{st["art"]["approved"][c["scene"]]["version"]} stays in the film until you decide)', 'href': 'art'}
           for c in st['art']['concepts'].values() if st['art']['approved'].get(c['scene'], {}).get('concept') == c['id']
           and c['versions'][-1]['v'] > st['art']['approved'][c['scene']]['version'] and not c['versions'][-1].get('status')])
    sbl = st['storyboards'][-1] if st['storyboards'] else None
    grp('storyboard', 'Storyboard', 'storyboard', [{'what': f'Approve storyboard v{sbl["v"]} (every scene\'s visual)', 'href': 'storyboard'}] if sbl and not sbl.get('decision') else [])
    grp('draft', 'Draft film', 'draft', [{'what': f'Watch draft {r["id"]} and decide', 'href': 'draft'} for r in st['renders'] if r.get('state') == 'ok' and not r.get('decision')])
    grp('review', 'Review findings', 'review', [{'what': f'{f["severity"]}: {f["code"]} · {f.get("scene") or "film"}', 'href': 'review', 'severity': f['severity']}
                                               for f in st['review']['findings'].values() if not f['decision']]
        + [{'what': f'Correction task: {t["what"]} ({t.get("scene") or "film"})', 'href': 'review'} for t in st['fix_tasks'] if t['status'] == 'open'])
    stale = bool(st['gate']['plan']) and _plan_stale(st)
    if st['gate']['plan'] and not st['gate'].get('authorized'):
        env = [b for b in st['gate']['plan']['blockers'] if 'disabled in this environment' in b]
        grp('gate', 'Final voice (paid) — blocked until', 'gate',
            ([{'what': STALE_PLAN, 'href': 'gate', 'blocker': True}] if stale else
             [{'what': b, 'href': 'gate', 'blocker': True} for b in st['gate']['plan']['blockers'] if b not in env])
            + [{'what': b + ' — not a decision: this workspace never runs paid generation', 'href': 'gate', 'wait': True} for b in env])
    st['inbox_groups'] = G
    # scene by scene: what is done for each line of the latest script
    lines = S.read_json(pid, latest['file'])['lines'] if latest else []
    sb_sc = {}
    if st['storyboards']:
        for x in st['storyboards'][-1]['scenes']: sb_sc[x['id']] = x
    open_f = {}
    for f in st['review']['findings'].values():
        if not f['decision'] and f.get('scene'): open_f[f['scene']] = open_f.get(f['scene'], 0) + 1
    st['scene_status'] = [{'id': l['id'], 'text': l['text'][:60],
                           'voice': (tk[st['voice']['by_line'][l['id']][-1]]['status'] if l['id'] in st['voice']['by_line'] else 'none'),
                           'art': ('approved' if l['id'] in st['art']['approved'] else 'selected' if l['id'] in st['art']['selected'] else
                                   'concepts' if l['id'] in st['art']['by_scene'] else 'brief default'),
                           'start': sb_sc.get(l['id'], {}).get('start'), 'dur': sb_sc.get(l['id'], {}).get('dur'),
                           'findings': open_f.get(l['id'], 0)} for l in lines]
    ok_r = [r for r in st['renders'] if r.get('state') == 'ok']
    st['latest_render'] = ok_r[-1] if ok_r else None
    st['inbox'] = {'script_flags': sum(1 for f in st['flags'] if f['status'] == 'open'),
                   'voice_flags': sum(1 for f in st['voice']['flags'] if f['status'] == 'open'),
                   'findings_open': sum(1 for f in st['review']['findings'].values() if not f['decision']),
                   'fix_tasks_open': sum(1 for t in st['fix_tasks'] if t['status'] == 'open'),
                   'pending_approvals': len(pend)}
    blockers = []
    if st['voice_profile'] and st['voice_profile']['status'] != 'usable':
        blockers.append({'what': f"Final voice {st['voice_profile']['name']} not authorized for this film", 'why': st['voice_profile']['why']})
    for i, j in enumerate(st['jobs']):
        later_ok = any(k['kind'] == j['kind'] and k['state'] == 'finished' and k['at'] >= j['at'] for k in st['jobs'][i + 1:])
        if j['state'] in ('failed', 'interrupted') and not later_ok:          # a later successful run clears it
            blockers.append({'what': f"{j['what']} {j['state']}", 'why': j.get('error', 'the server stopped while it ran'), 'job': j['id']})
    if st['gate']['plan']:
        if stale: blockers.append({'what': STALE_PLAN, 'why': 'final gate'})
        else:
            for b in st['gate']['plan']['blockers']: blockers.append({'what': b, 'why': 'final gate'})
    st['blockers'] = blockers
    if st['scripts']:
        latest = st['scripts'][-1]
        st['script_latest'] = S.read_json(pid, latest['file'])
        st['script_versions'] = {s['v']: S.read_json(pid, s['file'])['lines'] for s in st['scripts']}
    if st['research']:
        st['research_data'] = S.research(pid)
    try:
        st['narration'] = voice.narration(S, pid, st)
    except Refused:
        st['narration'] = None
    if st['art'].get('brief'):
        st['brief'] = S.read_json(pid, st['art']['brief'])
    if st['storyboards']:
        st['storyboard'] = S.read_json(pid, st['storyboards'][-1]['file'])
    st['support'] = art.support_matrix(S.profile(st['brand']))
    st['art_changes'] = {cid: art.effective_changes(c['technique'], c['versions'][-1].get('params', c['params']), c['versions'][-1].get('theme', c['theme']))
                         for cid, c in st['art']['concepts'].items() if c.get('support') == 'rendered'}
    st['flag_kinds'], st['vflag_kinds'], st['stage_names'] = FLAG_KINDS, VFLAG_KINDS, STAGE_NAMES
    st['revisions'] = art.REVISIONS
    st['paid_enabled'] = os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') == '1'
    if st['gate']['plan']:
        st['gate']['plan'] = {k: v for k, v in st['gate']['plan'].items() if k != 'plan'}
        st['gate']['plan_stale'] = _plan_stale(st)
    try:
        st['research_terms'] = [{'ar': t['ar'], 'term': t['term'], 'default': t.get('final', 'latin'), 'decision': (st['gate'].get('terms') or {}).get(t['ar'])}
                                for t in (S.research(pid) or {}).get('terms', [])]
    except Exception:
        st['research_terms'] = []
    st['history'] = st['history'][-200:]
    return st
