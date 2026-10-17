"""Co-Pilot actions on the Studio store (mixed into studio.store.Studio) and how they fold into the project state.

Every Co-Pilot change is one 'studio' event like any other (same log, same request ids, same history). Owner gates
(cp_gate) are the only way an owner decision reaches the classic decisions (research, script, takes, draft,
findings, final plan): the gate checks first that what the owner saw is still exactly what is there (content hash),
then records the classic decisions it stands for, then itself. Nothing the AI does is recorded as an owner decision:
AI work is recorded with actor 'copilot' (or 'reviewer' / 'system') and shown as AI reviewed.
"""
from __future__ import annotations
import json, re, time

from . import approvals as A

MODES = {'copilot': 'Co-Pilot', 'manual': 'Manual (classic Studio)', 'auto': 'Auto (not yet implemented)'}
FORMATS = ['9:16 vertical, Reels / TikTok', '9:16 vertical, YouTube Shorts']
WORKERS = ['mock', 'claude-code']
SYSTEM_ACTORS = ('system', 'copilot', 'reviewer')
SAFE_KEYS = {'text_size', 'zoom', 'slower', 'theme', 'gap', 'first_in'}


def _refused(msg):
    from ..studio.store import Refused
    return Refused(msg)


def _owner(actor):
    if actor in SYSTEM_ACTORS:
        raise _refused('only the owner can make this decision')


def _system(actor):
    if actor not in SYSTEM_ACTORS:
        raise _refused('this is recorded by the Co-Pilot, not sent from the page')


def _cov(iv, a, b):
    """Seconds of [a, b] covered by the merged intervals iv."""
    from ..studio.store import _merge
    return sum(max(0.0, min(y, b) - max(x, a)) for x, y in _merge(iv))


# Which actions a project's mode allows (checked on the server for every action, whoever sends it):
#  - Co-Pilot work (the owner's Co-Pilot decisions and everything the Co-Pilot records) only on a Co-Pilot project;
#  - on a Co-Pilot project the owner's classic decisions only as part of a Co-Pilot gate (never on their own), so no
#    classic screen or script can approve around a gate;
#  - always allowed: switching mode, settings, the AI budget, pause/resume/stop, and the record of an AI call's cost.
CP_ANY_MODE = {'cp_mode', 'cp_settings', 'cp_ai_budget', 'cp_control', 'cp_ai_call'}
OWNER_ANY_MODE = {'set_voice'}                       # chosen while a project is created (before or after its mode is recorded)


class CopilotActions:
    def _mode_guard(self, pid, action, actor):
        mode = self.state(pid)['copilot']['mode']
        if action.startswith('cp_'):
            if action in CP_ANY_MODE or mode == 'copilot': return
            raise _refused('this project is in Manual mode: switch back to the Co-Pilot first' if mode == 'manual'
                           else 'this is a classic project: the Co-Pilot does not change it')
        if mode == 'copilot' and actor not in SYSTEM_ACTORS and action not in OWNER_ANY_MODE and not getattr(self, '_cp_depth', 0):
            raise _refused('this project is run by the Co-Pilot: decide in the Studio, or switch to Manual first')

    # ------------------------------------------------------------------ mode, settings, controls, budget
    def a_cp_mode(self, pid, a, actor):
        _owner(actor)
        m = a.get('mode')
        if m == 'auto':
            raise _refused('Auto mode is not yet implemented')
        if m not in ('copilot', 'manual'):
            raise _refused('mode must be copilot or manual')
        st = self.state(pid)
        if st['copilot']['mode'] == m:
            raise _refused(f'already in {MODES[m]} mode')
        if st['copilot']['mode'] is None and (st['scripts'] or self.research(pid)):     # work done in the classic Studio stays classic
            raise _refused('this is a classic project: the Co-Pilot does not change it')
        return 'copilot', {'mode': m, 'from': st['copilot']['mode'], 'note': a.get('note', '')}

    def a_cp_settings(self, pid, a, actor):
        _owner(actor)
        out = {}
        if 'duration_s' in a:
            d = a['duration_s']
            if not isinstance(d, (int, float)) or not 20 <= d <= 180: raise _refused('duration must be 20–180 seconds')
            out['duration_s'] = int(d)
        if 'format' in a:
            if a['format'] not in FORMATS: raise _refused(f'format must be one of {FORMATS}')
            out['format'] = a['format']
        if 'worker' in a:
            if a['worker'] not in WORKERS: raise _refused(f'worker must be one of {WORKERS}')
            out['worker'] = a['worker']
        if 'model' in a:
            out['model'] = a['model'] or None
        if not out: raise _refused('nothing to change')
        return 'copilot', out

    def a_cp_control(self, pid, a, actor):
        _owner(actor)
        op = a.get('op')
        st = self.state(pid)
        cp = st['copilot']
        if op not in ('pause', 'resume', 'stop', 'retry'):
            raise _refused('op must be pause, resume, stop or retry')
        if cp['mode'] != 'copilot' and op in ('resume', 'retry'):
            raise _refused('switch back to Co-Pilot mode first')
        if op == 'retry':
            if not a.get('key'): raise _refused('which step to retry?')
            return 'copilot', {'op': op, 'key': a['key']}
        if op == 'pause' and cp['run'] != 'running': raise _refused('the Co-Pilot is not running')
        if op == 'resume' and cp['run'] == 'running': raise _refused('the Co-Pilot is already running')
        return 'copilot', {'op': op}

    def a_cp_ai_budget(self, pid, a, actor):
        _owner(actor)
        usd = a.get('usd')
        if not isinstance(usd, (int, float)) or usd < 0 or usd > 50:
            raise _refused('give the AI usage budget in US dollars (0–50)')
        if len((a.get('note') or '').strip()) < 8:
            raise _refused('write why you authorize this AI usage (kept in the history)')
        return 'copilot', {'usd': round(float(usd), 2), 'note': a['note'].strip()}

    def a_cp_ai_call(self, pid, a, actor):
        _system(actor)
        for k in ('cost_usd', 'reserved_usd'):
            if a.get(k) is not None and (not isinstance(a[k], (int, float)) or a[k] < 0):
                raise _refused(f'{k} must be a positive number')
        return 'copilot', a

    # ------------------------------------------------------------------ records written by the Co-Pilot
    def a_cp_direction(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_check(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_ready(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_stage(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_script_meta(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_voice_mix(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_style(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_asset_needs(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_exception(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_scene(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_film(self, pid, a, actor):
        _system(actor); return 'copilot', a

    def a_cp_task(self, pid, a, actor):
        _system(actor); return 'copilot', a

    # ------------------------------------------------------------------ owner edits between gates
    def a_cp_hook(self, pid, a, actor):
        """Gate 2: use another hook. Makes a NEW script version whose first line is that hook (approved like any other)."""
        _owner(actor)
        st = self.state(pid)
        h = next((o for o in st['hooks']['options'] if o['id'] == a.get('hook')), None)
        if h is None: raise _refused('unknown hook')
        if st['hooks']['selected'] == h['id']: raise _refused('this hook is already the opening line')
        base = self._version_lines(pid, st['scripts'][-1])['lines']
        lines = [{'id': 'h', 'text': h['spoken'], 'role': 'hook'}] + [l for l in base if l.get('role') != 'hook']
        rid = a.get('_rid', 'x')
        self.act(pid, 'hook_select', {'hook': h['id'], 'note': 'owner chose this hook (Gate 2)'}, actor, rid + '-sel')
        r = self.act(pid, 'script_version', {'lines': lines, 'note': f'hook {h["id"]} as the opening line', 'author': 'owner'}, actor, rid + '-v')
        return 'copilot', {'hook': h['id'], 'v': r['result']['v']}

    def a_cp_line_edit(self, pid, a, actor):
        """Gate 2 sentence editor: a new version in which only this line changes."""
        _owner(actor)
        st = self.state(pid)
        if not st['scripts']: raise _refused('no script yet')
        latest = st['scripts'][-1]
        base = self._version_lines(pid, latest)['lines']
        text = (a.get('text') or '').strip()
        ln = next((l for l in base if l['id'] == a.get('line')), None)
        if ln is None: raise _refused(f'no line {a.get("line")} in v{latest["v"]}')
        if not text: raise _refused('the sentence is empty')
        if text == ln['text']: raise _refused('nothing changed')
        if ln.get('role') == 'hook': raise _refused('the opening line is the hook: choose or edit a hook instead')
        lines = [dict(l, text=text) if l['id'] == ln['id'] else l for l in base]
        r = self.act(pid, 'script_version', {'lines': lines, 'note': f'owner edited {ln["id"]}', 'author': 'owner'}, actor, a.get('_rid', 'x') + '-v')
        return 'copilot', {'line': ln['id'], 'v': r['result']['v'], 'from_v': latest['v']}

    def a_cp_pron(self, pid, a, actor):
        """Pronunciation dictionary for the DRAFT voice: add (owner or AI proposal) or decide on an AI proposal."""
        st = self.state(pid)
        op = a.get('op', 'add')
        if op == 'decide':
            _owner(actor)
            e = next((x for x in st['copilot']['pron'] if x['id'] == a.get('id')), None)
            if e is None: raise _refused('unknown pronunciation entry')
            if a.get('decision') not in ('approved', 'rejected'): raise _refused('decision must be approved or rejected')
            return 'voice', {'op': 'decide', 'id': e['id'], 'decision': a['decision']}
        word, respell = (a.get('word') or '').strip(), (a.get('respell') or '').strip()
        if not word or not respell: raise _refused('give the word and how the draft voice should read it')
        if word == respell: raise _refused('the spelling is the same as the word')
        src = 'owner' if actor not in SYSTEM_ACTORS else 'ai'
        from ..studio import checks
        n = len(st['copilot']['pron']) + 1
        lines = a.get('lines') or [l for l, x in (st['voice'].get('lines') or {}).items() if word in checks.words(x['text'])]
        return 'voice', {'op': 'add', 'id': f'pr{n}', 'word': word, 'respell': respell, 'lines': lines, 'source': src,
                         'kind': a.get('kind', 'pronunciation'), 'why': a.get('why', ''), 'status': 'approved' if src == 'owner' else 'proposed',
                         'rule': {'id': f'cp-{pid}-pr{n}', 'scope': f'project:{pid}', 'surface': checks.bare(word), 'status': 'approved',
                                  'providers': {'gtts': {'mode': 'spoken', 'spoken': respell, 'article_ok': True}}, 'lines': lines}}

    def a_cp_voice_adjust(self, pid, a, actor):
        """Draft-voice speed and pauses, processed locally (free). Makes a new take; the original stays."""
        _owner(actor)
        st = self.state(pid)
        x = (st['voice'].get('lines') or {}).get(a.get('line'))
        if not x or not x['take']: raise _refused('this line has no draft take yet')
        sp, pb, pa = a.get('speed', 1.0), a.get('pause_before', 0.0), a.get('pause_after', 0.0)
        for v, lo, hi, name in ((sp, .8, 1.25, 'speed'), (pb, 0, 1.5, 'pause before'), (pa, 0, 1.5, 'pause after')):
            if not isinstance(v, (int, float)) or not lo <= v <= hi: raise _refused(f'{name} must be {lo}–{hi}')
        if sp == 1.0 and pb == 0 and pa == 0: raise _refused('nothing to change')
        base = st['voice']['takes'][x['take']]
        src = base.get('processed', {}).get('from', base['id'])
        return 'voice', {'line': a['line'], 'take': src, 'speed': round(float(sp), 3), 'pause_before': round(float(pb), 2), 'pause_after': round(float(pa), 2)}

    def a_cp_asset(self, pid, a, actor):
        """Asset library: an owner upload or link, its licence evidence, or withdrawing it. Never deleted."""
        st = self.state(pid)
        op = a.get('op', 'add')
        assets = st['copilot']['assets']
        if op == 'add':
            _owner(actor)
            if not a.get('file') and not a.get('url'): raise _refused('upload a file or give a link')
            if a.get('use') not in ('evidence', 'illustration'): raise _refused('say whether it is a genuine record (evidence) or an illustration')
            aid = f'as{len(assets) + 1}'
            return 'assets', {'op': op, 'id': aid, 'slot': a.get('slot') or '', 'scene': a.get('scene') or '', 'file': a.get('file'), 'url': a.get('url'),
                              'name': a.get('name', ''), 'credit': a.get('credit', ''), 'use': a['use'], 'source': 'upload' if a.get('file') else 'link',
                              'what': a.get('what', '')}
        x = assets.get(a.get('id'))
        if x is None: raise _refused('unknown asset')
        if op == 'licence':
            _owner(actor)
            kind = a.get('licence')
            ev = (a.get('evidence') or '').strip()
            if kind not in ('owner_owned', 'licensed', 'public_domain', 'cc'):
                raise _refused('licence must be owner_owned, licensed, public_domain or cc')
            if kind == 'owner_owned':
                if not a.get('declare'): raise _refused('confirm that you own this picture or its rights')
                ev = ev or 'owner declaration'
            elif a.get('evidence_file'):
                f = a['evidence_file']
                if not (isinstance(f, str) and f.startswith('blobs/') and self.path(pid, f).is_file()):
                    raise _refused('the licence document must be a file uploaded to this project')
                if any(f == y.get('file') for y in assets.values()):
                    raise _refused('a picture is not its own licence: give the licence document or the page that states the licence')
            else:
                from .factcheck import URL, _real_host
                links = [m.group(0) for m in URL.finditer(ev) if _real_host(m.group(1))]
                if not links:
                    raise _refused('licence evidence needed: the page that states the licence (a link to a real site) or the licence document')
                if x.get('url') and all(l.rstrip('/') == x['url'].rstrip('/') for l in links):
                    raise _refused('the picture\'s own address is not its licence: link the page that states the licence')
            return 'assets', {'op': op, 'id': x['id'], 'licence': kind, 'evidence': ev, 'evidence_file': a.get('evidence_file'),
                              'holder': a.get('holder', ''), 'restrictions': a.get('restrictions', '')}
        if op == 'withdraw':
            _owner(actor)
            if len((a.get('note') or '').strip()) < 4: raise _refused('say why')
            return 'assets', {'op': op, 'id': x['id'], 'note': a['note']}
        raise _refused('op must be add, licence or withdraw')

    def a_cp_exception_decision(self, pid, a, actor):
        _owner(actor)
        st = self.state(pid)
        x = next((e for e in st['copilot']['exceptions'] if e['id'] == a.get('id')), None)
        if x is None or x['status'] != 'open': raise _refused('no open exception with that id')
        if a.get('decision') not in x['options']: raise _refused(f'choose one of {x["options"]}')
        if a['decision'] in ('accept_best', 'keep_fallback') and len((a.get('note') or '').strip()) < 4:
            raise _refused('say why you accept it (kept in the history)')
        ch = {}
        if a['decision'] == 'remove_banner':
            ch = {'banner': 'none'}
        elif a['decision'] == 'retry_with_change':
            from .scenes import OWNER_KEYS
            ch = {k: str(v) for k, v in (a.get('changes') or {}).items()}
            if not ch or set(ch) - OWNER_KEYS: raise _refused(f'choose the changes to try ({", ".join(sorted(OWNER_KEYS))})')
        return 'copilot', {'id': x['id'], 'decision': a['decision'], 'note': a.get('note', ''), 'changes': ch, 'scene': x.get('scene')}

    def a_cp_comment(self, pid, a, actor):
        """Gate 5: a comment at a time code. It becomes a task on the scene playing at that moment."""
        _owner(actor)
        st = self.state(pid)
        films = [f for f in st['copilot']['films'] if f.get('state') == 'ok']
        if not films: raise _refused('no film to comment on')
        f = films[-1]
        if a.get('film') != f['n']: raise _refused(f'comment on the latest film (v{f["n"]})')
        t = a.get('t')
        if not isinstance(t, (int, float)) or not 0 <= t <= f['seconds']: raise _refused('time code out of range')
        text = (a.get('text') or '').strip()
        if len(text) < 3: raise _refused('write the comment')
        sc = next((s for s in f['timeline'] if s['start'] <= t < s['end'] and s['id'] != 'endcard'), None)   # the end card is not a scene
        n = len(st['copilot']['comments']) + 1
        return 'copilot', {'id': f'cm{n}', 'film': f['n'], 't': round(t, 2), 'scene': sc['id'] if sc else 'endcard', 'text': text,
                           'task': {'id': f'tk{len(st["copilot"]["tasks"]) + 1}', 'scene': sc['id'] if sc else None, 'source': f'comment cm{n}', 'what': text}}

    def a_cp_finding(self, pid, a, actor):
        """Gate 5: resolve a major finding by explaining why it stays (a critical one must be fixed, never dismissed)."""
        _owner(actor)
        st = self.state(pid)
        f = st['review']['findings'].get(a.get('finding'))
        if f is None or f['decision']: raise _refused('no open finding with that id')
        note = (a.get('note') or '').strip()
        if f['severity'] == 'critical':
            from .factcheck import override_ok, connected_claims
            if f['code'] not in ('CLAIM_ON_SCREEN', 'YEAR_NOT_IN_RESEARCH'):
                raise _refused('a critical finding cannot be dismissed: it must be fixed')
            ap = [x for x in st['scripts'] if x['status'] == 'approved']
            v = str(ap[-1]['v']) if ap else ''
            mc = next((c for c in reversed(st['copilot']['checks']) if c['target'] == 'script' and str(c['ref']) == v and c['kind'] == 'merged'), None)
            sc = f.get('scene')
            conn = connected_claims((mc or {}).get('lines', {}).get(sc), ((st['copilot']['script_meta'].get(v) or {}).get('claims') or {}).get(sc))
            if not override_ok(note, self.research(pid), conn):
                raise _refused('a factual finding can only be overruled with evidence for this scene and a sentence saying why: '
                               + (f'cite {", ".join(conn)} or a source link' if conn else 'no research claim is linked to it, so cite a source link'))
        if len(note) < 8: raise _refused('say why it can stay (kept in the review history)')
        self.act(pid, 'finding_decision', {'finding': f['id'], 'decision': 'dismissed', 'note': 'owner (Gate 5): ' + note}, actor, a.get('_rid', 'x') + '-fd')
        return 'review', {'finding': f['id'], 'note': note}

    # ------------------------------------------------------------------ owner gates
    def a_cp_gate(self, pid, a, actor):
        _owner(actor)
        g, d = a.get('gate'), a.get('decision')
        if g not in A.GATES: raise _refused('unknown gate')
        if d not in ('approved', 'changes_requested', 'rejected'): raise _refused('decision must be approved, changes_requested or rejected')
        st = self.state(pid)
        cp = st['copilot']
        cur = A.current(st)[g]
        if cur is None: raise _refused(f'{A.GATE_NAME[g][0]}: nothing to decide yet')
        if a.get('content_hash') != cur['hash']:
            raise _refused('what you reviewed has changed since the page loaded: look at the new version first')
        last = A.last(cp, g)
        if last and last['content_hash'] == cur['hash'] and last['decision'] == d and \
                (g != 'G4' or (last.get('style') or {}).get('id') == a.get('choice')):
            raise _refused(f'already {d} for this version')
        if d != 'approved' and len((a.get('note') or '').strip()) < 3:
            raise _refused('say what should change')
        val = A.validity(st)
        for u in A.DEPENDS[g]:
            if d == 'approved' and not val[u]['valid']:
                raise _refused(f'approve {A.GATE_NAME[u][0]} ({u}) first' + (f': {val[u]["why"]}' if val[u]['why'] else ''))
        rid = a.get('_rid') or 'g'
        out = getattr(self, '_gate_' + g)(pid, st, cp, a, cur, d, actor, rid) or {}
        return 'copilot', {'gate': g, 'decision': d, 'ref': cur['ref'], 'content_hash': cur['hash'],
                           'settings_hash': A.upstream_hash(st, g, val), 'note': a.get('note', ''), 'by': actor, **out}

    def _gate_G1(self, pid, st, cp, a, cur, d, actor, rid):
        dr = cp['directions'][-1]
        if not any(c['target'] == 'direction' and c['ref'] == dr['v'] for c in cp['checks']):
            raise _refused('the independent research check has not finished')
        if st['research'] and st['research']['status'] == 'waiting':
            self.act(pid, 'research_decision', {'decision': 'approved' if d == 'approved' else 'changes_requested',
                                                'note': ('Gate 1: ' + a.get('note', '')).strip()}, actor, rid + '-rd')
        return {}

    def _gate_G2(self, pid, st, cp, a, cur, d, actor, rid):
        from .factcheck import override_ok
        sv = st['scripts'][-1]
        approved_already = sv['status'] == 'approved'                      # e.g. approved in Manual mode: confirm it here
        if sv['status'] not in ('draft', 'approved') or (approved_already and d != 'approved'):
            raise _refused(f'script v{sv["v"]} is already {sv["status"]}')
        rev = next((c for c in reversed(cp['checks']) if c['target'] == 'script' and c['ref'] == sv['v'] and c['kind'] == 'merged'), None)
        out = {}
        if d == 'approved':
            if rev is None: raise _refused(f'the AI fact check and editor review of v{sv["v"]} have not finished')
            lines = self._version_lines(pid, sv)['lines']
            hook = next((o for o in st['hooks']['options'] if o['id'] == st['hooks']['selected']), None)
            if hook is None or not lines or lines[0].get('role') != 'hook' or lines[0]['text'] != hook['spoken']:
                raise _refused('the opening line must be the chosen hook: choose a hook')
            ov, ack = a.get('overrides') or {}, set(a.get('ack') or [])
            crit = [l for l, x in rev['lines'].items() if x['severity'] == 'critical']
            major = [l for l, x in rev['lines'].items() if x['severity'] == 'major']
            from .factcheck import connected_claims
            wc = ((cp['script_meta'].get(str(sv['v'])) or {}).get('claims') or {})
            conn = {l: connected_claims(rev['lines'][l], wc.get(l)) for l in crit}
            missing = [l for l in crit if not override_ok(ov.get(l, ''), self.research(pid), conn[l])]
            if missing:
                hint = '; '.join(f'{l}: cite {", ".join(conn[l])} or a source link' if conn[l] else f'{l}: no research claim is linked to it, so cite a source link' for l in missing)
                raise _refused(f'critical fact-check result on {", ".join(missing)}: fix the line, or override it with evidence for THIS line and a sentence saying why ({hint})')
            if set(major) - ack:
                raise _refused(f'confirm you have read the warnings on {", ".join(sorted(set(major) - ack))}')
            kw = [c for c in sv['checks'] if c['severity'] == 'critical']
            note = 'Gate 2 approved by the owner' + ''.join(f'; {l}: {ov[l]}' for l in crit)
            if kw and not crit:
                note += '; the research rule flagged ' + ', '.join(sorted({c['line'] for c in kw})) + ' and the owner read it: ' + (a.get('note') or 'checks disagree; fact checker found no contradiction')
            if not approved_already:
                self.act(pid, 'script_decision', {'v': sv['v'], 'decision': 'approved', 'override': bool(kw), 'note': note}, actor, rid + '-sd')
            st2 = self.state(pid)
            if not st2['hooks']['delivery']:
                meta = cp['script_meta'].get(str(sv['v'])) or {}
                pay = (meta.get('hooks') or {}).get(hook['id']) or 'l2'
                self.act(pid, 'hook_delivery', {'decision': 'delivered', 'line': pay, 'note': 'confirmed with the script at Gate 2'}, actor, rid + '-hd')
            out = {'overrides': {l: ov[l] for l in crit}, 'ack': sorted(ack)}
        else:
            self.act(pid, 'script_decision', {'v': sv['v'], 'decision': 'rejected' if d == 'rejected' else 'changes_requested',
                                              'note': a.get('note', '')}, actor, rid + '-sd')
        return out

    def _gate_G3(self, pid, st, cp, a, cur, d, actor, rid):
        if d != 'approved':
            raise _refused('to change the voice, tap the word or line and correct it (spelling, tashkeel, speed, pauses); then approve')
        mix = cp['voice_mix']
        if not mix or mix['takes'] != cur['takes']:
            raise _refused('the play-all narration is being rebuilt for the latest takes: play it again')
        if (a.get('playback') or {}).get('of') != mix['file']:          # the listening belongs to the play-all that was heard
            raise _refused('the play-all narration changed after you listened: play it again')
        cov = (a.get('playback') or {}).get('covered') or []
        vl = st['voice']['lines']
        todo, short = [], []
        for seg in mix['segments']:
            if st['voice']['takes'][seg['take']]['status'] == 'approved': continue      # already approved and unchanged
            heard = _cov(cov, seg['start'], seg['end'])
            if heard < 0.8 * (seg['end'] - seg['start']): short.append(seg['line'])
            else: todo.append(seg)
        if short:
            raise _refused('listen to every changed line before approving: ' + ', '.join(short))
        flags = [f['id'] for f in cp['voice_qa'].get('flags', []) if f['status'] == 'open' and f['take'] in cur['takes'].values()]
        if set(flags) - set(a.get('ack') or []):
            raise _refused('confirm the uncertain words first: ' + ', '.join(sorted(set(flags) - set(a.get('ack') or []))))
        for seg in todo:
            rel = [[max(0, x - seg['start']), min(seg['end'], y) - seg['start']] for x, y in cov if y > seg['start'] and x < seg['end']]
            self.act(pid, 'take_decision', {'take': seg['take'], 'decision': 'approved', 'note': 'Gate 3: heard in play-all',
                                            'playback': {'covered': rel, 'source': 'play-all'}}, actor, f'{rid}-td-{seg["line"]}')
        prop = [e['id'] for e in cp['pron'] if e['status'] == 'proposed']
        return {'lines': [s['line'] for s in todo], 'pron_approved': prop, 'ack': sorted(set(a.get('ack') or []))}

    def _gate_G4(self, pid, st, cp, a, cur, d, actor, rid):
        s = cp['styles'][-1]
        if d != 'approved': return {}
        ch = next((x for x in s['directions'] if x['id'] == a.get('choice')), None)
        if ch is None: raise _refused('choose one of the styles')
        if not ch.get('ready'): raise _refused(f'{ch["name"]} cannot be used yet: {ch.get("why_not", "not ready")}')
        return {'style': {'id': ch['id'], 'version': ch['version'], 'board': ch['board'], 'params_hash': ch['params_hash'],
                          'references': ch.get('stills', [])}}

    def _gate_G5(self, pid, st, cp, a, cur, d, actor, rid):
        f = next(x for x in cp['films'] if x['n'] == cur['ref'])
        if d != 'approved':
            return {}
        pb = a.get('playback') or {}
        if pb.get('of') != f['n']:
            raise _refused(f'the watching you did was of another draft: watch film v{f["n"]}')
        from ..studio.store import _heard
        if _heard(pb, f['seconds']) < 0.8 * f['seconds']:
            raise _refused(f'watch the whole draft before approving: {_heard(pb, f["seconds"]):.0f} s of {f["seconds"]:.0f} s watched')
        bad = [s for s, ok in f.get('scene_valid', {}).items() if not ok]
        if bad: raise _refused('scenes changed since this film was made: ' + ', '.join(bad))
        fs = [x for x in st['review']['findings'].values() if x['run'] in f['reviews'] and not x['decision']]
        crit = [x['id'] for x in fs if x['severity'] in ('critical', 'major')]
        if crit:
            raise _refused(f'{len(crit)} critical or major finding(s) are still open: they must be fixed (or a major one explained) first')
        need = {x['id'] for x in fs if x['severity'] == 'minor'}
        if need - set(a.get('ack') or []):
            raise _refused(f'acknowledge the {len(need - set(a.get("ack") or []))} minor issue(s) that would remain')
        for x in fs:
            self.act(pid, 'finding_decision', {'finding': x['id'], 'decision': 'dismissed',
                                               'note': 'owner acknowledged at Gate 5' + (f': {a["note"]}' if a.get('note') else '')}, actor, f'{rid}-fd-{x["id"]}')
        sb = st['storyboards'][-1]
        if sb['v'] == f['storyboard_v'] and not sb.get('decision'):
            self.act(pid, 'storyboard_decision', {'v': sb['v'], 'decision': 'approved', 'note': f'approved with film v{f["n"]} (Gate 5)'}, actor, rid + '-sb')
        r = next(x for x in st['renders'] if x['id'] == f['render'])
        if not r.get('decision'):
            self.act(pid, 'render_decision', {'render': r['id'], 'decision': 'approved_as_draft', 'note': 'Gate 5', 'playback': pb}, actor, rid + '-rd')
        return {'ack': sorted(need), 'scenes': f['scenes']}

    def _gate_G6(self, pid, st, cp, a, cur, d, actor, rid):
        if d != 'approved':
            return {}
        self.act(pid, 'gate_authorize', {'plan': cur['ref'], 'confirm_text': a.get('confirm_text', '')}, actor, rid + '-ga')
        from ..studio.gate import ledger
        plan = st['gate']['plan']
        aid = ledger(self).create_approval(plan['hash'], pid, 'elevenlabs', plan['chars_total'], actor, ttl_s=6 * 3600)
        return {'approval': aid, 'single_use': True, 'expires_in_s': 6 * 3600}


# ====================================================================== fold
def empty() -> dict:
    return {'mode': None, 'run': 'idle', 'paused_by': None, 'modes': [], 'settings': {'worker': 'mock', 'duration_s': 75, 'format': FORMATS[0], 'platform': 'reels',
                                                                   'max_rounds': 2, 'model': None},
            'directions': [], 'gates': {g: [] for g in A.GATES}, 'ready': {}, 'checks': [], 'script_meta': {},
            'ai': {'calls': [], 'budget_usd': 0.0, 'spent_usd': 0.0, 'budget_history': []}, 'pron': [], 'voice_mix': None,
            'voice_qa': {'flags': [], 'by_take': {}}, 'adjust': [], 'styles': [], 'assets': {}, 'asset_needs': [], 'exceptions': [],
            'scenes': {}, 'films': [], 'comments': [], 'tasks': [], 'stages': [], 'retries': [], 'controls': []}


def fold(st: dict, e: dict):
    """Apply one cp_* event (or a classic event the Co-Pilot cares about) to st['copilot']."""
    cp = st['copilot']
    act, r = e['status'], e['data'].get('result') or {}
    at = e['at']
    if act == 'cp_mode':
        cp['mode'] = r['mode']; cp['modes'].append({'mode': r['mode'], 'at': at, 'by': e['actor'], 'note': r.get('note', '')})
        if r['mode'] == 'copilot' and r.get('from') is None: cp['run'] = 'running'
        if r['mode'] == 'manual': cp['run'] = 'stopped'
    elif act == 'cp_settings':
        cp['settings'].update(r)
    elif act == 'cp_control':
        cp['controls'].append({**r, 'at': at, 'seq': e['seq']})
        if r['op'] == 'pause': cp['run'] = 'paused'; cp['paused_by'] = 'owner'
        elif r['op'] == 'stop': cp['run'] = 'stopped'; cp['paused_by'] = 'owner'
        elif r['op'] == 'resume': cp['run'] = 'running'
        elif r['op'] == 'retry': cp['retries'].append(r['key']); cp['run'] = 'running'
    elif act == 'cp_ai_budget':
        cp['ai']['budget_usd'] = r['usd']; cp['ai']['budget_history'].append({**r, 'at': at})
    elif act == 'cp_ai_call':
        # a call is first recorded as 'started' with its whole cap reserved (a restart mid-call still counts it), then
        # replaced by its result; a failed call whose cost the CLI did not report keeps the reserved cap as its cost
        prev = next((c for c in cp['ai']['calls'] if c['id'] == r['id']), {})
        cp['ai']['calls'] = [c for c in cp['ai']['calls'] if c['id'] != r['id']] + [{**r, 'key': r.get('key') or prev.get('key'), 'at': at,
                                                                                     'seq': prev.get('seq', e['seq'])}]
        cp['ai']['spent_usd'] = round(sum(max(0.0, float(c.get('cost_usd') if c.get('cost_usd') is not None else c.get('reserved_usd') or 0))
                                          for c in cp['ai']['calls']), 6)
    elif act == 'cp_direction':
        cp['directions'].append({**r, 'at': at})
    elif act == 'cp_check':
        cp['checks'].append({**r, 'at': at})
    elif act == 'cp_ready':
        cp['ready'][r['gate']] = {**r, 'at': at}
    elif act == 'cp_stage':
        cp['stages'].append({**r, 'at': at})
    elif act == 'cp_script_meta':
        cp['script_meta'][str(r['v'])] = r
    elif act == 'cp_gate':
        cp['gates'][r['gate']].append({**r, 'at': at})      # the Co-Pilot carries on by itself (unless you paused or stopped it)
        if r['gate'] == 'G3' and r['decision'] == 'approved':
            for p in cp['pron']:
                if p['id'] in r.get('pron_approved', []): p['status'] = 'approved'
            for f in cp['voice_qa']['flags']:
                if f['id'] in r.get('ack', []): f['status'] = 'acknowledged'
    elif act == 'cp_hook':
        pass
    elif act == 'cp_pron':
        if r['op'] == 'add':
            # a new spelling for the same word on the same lines replaces the earlier one (two rules would compete)
            same = lambda x: x.get('surface') == r['rule']['surface'] and (not x.get('lines') or not r['lines'] or set(x['lines']) & set(r['lines']))
            if r['status'] == 'approved':
                for p in cp['pron']:
                    if p['status'] in ('approved', 'proposed') and same(p['rule']): p['status'] = 'superseded'
                st['voice']['rules'] = [x for x in st['voice']['rules'] if not same(x)]
            cp['pron'].append({**r, 'at': at})
            st['voice']['rules'] = [x for x in st['voice']['rules'] if x['id'] != r['rule']['id']] + [r['rule']]
        else:
            for p in cp['pron']:
                if p['id'] == r['id']:
                    p['status'] = r['decision']
                    st['voice']['rules'] = [x for x in st['voice']['rules'] if x['id'] != p['rule']['id']]
                    if r['decision'] == 'approved': st['voice']['rules'].append(p['rule'])
    elif act == 'cp_voice_adjust':
        cp['adjust'].append({**r, 'at': at})
    elif act == 'cp_voice_mix':
        if r.get('qa') is not None:
            prev = {f['id']: f['status'] for f in cp['voice_qa']['flags']}
            cp['voice_qa'] = {'flags': [dict(f, status=prev.get(f['id'], f['status'])) for f in r['qa']['flags']], 'by_take': r['qa']['by_take']}
        cp['voice_mix'] = {k: v for k, v in r.items() if k != 'qa'} | {'at': at}
    elif act == 'cp_style':
        cp['styles'].append({**r, 'at': at})
    elif act == 'cp_asset':
        if r['op'] == 'add':
            cp['assets'][r['id']] = {**r, 'licence': None, 'status': 'unverified', 'at': at, 'history': [{'op': 'add', 'at': at}]}
        else:
            x = cp['assets'][r['id']]
            x['history'].append({**r, 'at': at})
            if r['op'] == 'licence':
                x.update(licence={k: r[k] for k in ('licence', 'evidence', 'evidence_file', 'holder', 'restrictions')}, status='verified')
            elif r['op'] == 'withdraw':
                x['status'] = 'withdrawn'
    elif act == 'cp_asset_needs':
        cp['asset_needs'] = r['needs']
    elif act == 'cp_exception':
        prev = next((x for x in cp['exceptions'] if x['id'] == r['id']), None)
        if r.get('status') == 'resolved' and prev:          # resolved by what happened (e.g. licence evidence added)
            prev.update(status='resolved', decision=r.get('decision', 'resolved'), decision_note=r.get('note', ''), decided=at)
            return
        cp['exceptions'] = [x for x in cp['exceptions'] if not (x['id'] == r['id'])] + [{**r, 'status': 'open', 'at': at}]
        if cp['run'] == 'running' and r.get('pause', True): cp['run'] = 'paused'; cp['paused_by'] = 'exception'
    elif act == 'cp_exception_decision':
        for x in cp['exceptions']:
            if x['id'] == r['id']: x.update(status='decided', decision=r['decision'], decision_note=r['note'], changes=r.get('changes') or {}, decided=at)
        if cp['mode'] == 'copilot' and cp['run'] == 'paused' and cp.get('paused_by') == 'exception' and not any(x['status'] == 'open' for x in cp['exceptions']):
            cp['run'] = 'running'
    elif act == 'cp_scene':
        d = cp['scenes'].setdefault(r['scene'], {'versions': [], 'pick': None, 'picks': []})
        if r['op'] == 'version': d['versions'].append({**r, 'at': at})
        else: d['pick'] = {**r, 'at': at}; d['picks'].append(d['pick'])
    elif act == 'cp_film':
        for f in cp['films']:                              # a newer film started: an older one still 'running' was cut off
            if f['n'] != r['n'] and f.get('state') == 'running': f['state'] = 'interrupted'
        cp['films'] = [f for f in cp['films'] if f['n'] != r['n']] + [{**r, 'at': at}]
    elif act == 'cp_comment':
        cp['comments'].append({**r, 'at': at})
        cp['tasks'].append({**r['task'], 'status': 'open', 'at': at, 'film': r['film'], 't': r['t']})
    elif act == 'cp_task':
        found = False
        for t in cp['tasks']:
            if t['id'] == r['id']: t.update(r); found = True
        if not found: cp['tasks'].append({**r, 'at': at})
