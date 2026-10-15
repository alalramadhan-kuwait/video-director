"""Studio: a new video project from an idea to a draft film and a validated final-production plan (development only).

Saving and history
  * Everything a person or the system does is ONE append-only event (kind 'studio') in the dashboard event log.
    Files (script versions, takes, stills, renders, evidence) are content-addressed, written once and made read-only
    under VAR/studio/<project>/blobs. A project's state is rebuilt from its events every time it is read: saving is
    the event being written, reopening is replaying them, and the version history is the event list itself.
  * A status (approved, rejected, selected...) only ever comes from a decision event. A file appearing on disk
    never approves anything (tested).
  * Every write carries a request id. The same request sent twice (double tap, page refresh, retry) returns the
    first receipt as 'duplicate' and changes nothing.

Rules enforced here
  * One brand per project. A Time Keeper project loads the Time Keeper profile only; a Diabetes History profile,
    voice, palette or end card is refused (and the reverse).
  * Selecting is never approving: a selected hook, art concept or take still needs its own approval.
  * Approved script versions, takes and art versions are final; a change makes a NEW version and keeps the old.
  * A correction changes only the flagged word (checked by diffing the two versions before it is recorded).
  * Long work (draft voice, art samples, renders, review) runs as tracked tasks with counted units and measured
    times (events.py). A task that was running when the server stopped shows as interrupted and can be resumed.
  * Nothing here can reach a paid provider: the final step only builds and checks the plan (voice/plan.py).
"""
from __future__ import annotations
import hashlib, json, os, re, stat, threading, time, uuid
from pathlib import Path

import yaml

from ..events import EventLog, summarize
from . import checks
from ..copilot.actions import CopilotActions, empty as _cp_empty, fold as _cp_fold

ROOT = Path(__file__).resolve().parents[2]
STAGES = ['research', 'script', 'hook', 'voice', 'art', 'storyboard', 'draft', 'review', 'gate']
STAGE_NAMES = {'research': 'Research', 'script': 'Script', 'hook': 'Hook', 'voice': 'Draft voice', 'art': 'Art',
               'storyboard': 'Storyboard', 'draft': 'Draft video', 'review': 'Review', 'gate': 'Final voice plan'}
BRANDS = {
    'timekeeper': {'name': 'Time Keeper', 'profile': 'profiles/timekeeper-luxury-doc.yaml', 'style': 'tk-style'},
    'diabetes-history': {'name': 'Diabetes History', 'profile': 'profiles/diabetes-history-sci.yaml', 'style': 'dh'},
}
FLAG_KINDS = {'spelling': 'Spelling', 'pronunciation': 'Pronunciation', 'grammar': 'Grammar', 'fact': 'Fact',
              'dialect': 'Dialect / wording', 'other': 'Other'}
VFLAG_KINDS = {'wrong': 'Wrong word', 'english': 'Said in English', 'article': '«الـ» problem', 'vowel': 'Wrong vowel',
               'stress': 'Stress / rhythm', 'unclear': 'Unclear', 'other': 'Other'}


class Refused(Exception):
    """A request that breaks a rule. Nothing was recorded."""


def _slug(s: str) -> str:
    s = re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
    return s[:40] or 'project'



def _merge(iv):
    out = []
    for a, b in sorted((float(a), float(b)) for a, b in (iv or []) if float(b) > float(a)):
        if out and a <= out[-1][1] + 1e-6: out[-1][1] = max(out[-1][1], b)
        else: out.append([a, b])
    return out


def _heard(pb: dict, seconds: float) -> float:
    """Seconds of the media actually heard. The page sends the parts it heard ('covered'); a caller that sends only a total
    ('listened_s', the API and older pages) is taken at its word, capped at the length."""
    if 'covered' in pb:
        return sum(min(b, seconds) - max(a, 0) for a, b in _merge(pb['covered']) if min(b, seconds) > max(a, 0))
    return min(float(pb.get('listened_s', 0) or 0), seconds)


def _overlap(iv, s: float, e: float) -> float:
    return sum(max(0.0, min(b, e) - max(a, s)) for a, b in _merge(iv))

class Studio(CopilotActions):
    def __init__(self, var: Path):
        self.var = Path(var)
        self.root = self.var / 'studio'
        self.root.mkdir(parents=True, exist_ok=True)
        self.log = EventLog(self.var / 'events.sqlite')
        self.lock = threading.RLock()
        self.jobs: dict[str, dict] = {}          # live background jobs of THIS server process (lost on restart)
        from .engine import kill_orphans
        self.orphans_killed = kill_orphans(self.root)        # renders a previous server left running

    # ------------------------------------------------------------------ files
    def pdir(self, pid) -> Path:
        return self.root / pid

    def put(self, pid, data: bytes, ext: str) -> str:
        """Write-once, read-only, content-addressed file. Returns its relative path under the project."""
        h = hashlib.sha256(data).hexdigest()[:20]
        rel = f'blobs/{h}.{ext}'
        p = self.pdir(pid) / rel
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix('.tmp'); tmp.write_bytes(data); os.replace(tmp, p)
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        return rel

    def put_file(self, pid, path: Path, ext=None) -> str:
        return self.put(pid, Path(path).read_bytes(), ext or Path(path).suffix.lstrip('.'))

    def path(self, pid, rel) -> Path:
        p = (self.pdir(pid) / rel).resolve()
        if self.pdir(pid).resolve() not in p.parents:
            raise Refused('path outside the project')
        return p

    def read_json(self, pid, rel):
        return json.loads(self.path(pid, rel).read_text(encoding='utf-8'))

    # ------------------------------------------------------------------ events
    def events(self, pid=None):
        rows = self.log.rows(kind='studio', **({'project': pid} if pid else {}))
        return rows

    def _emit(self, pid, stage, action, actor, request_id, args, result):
        return self.log.emit('studio', pid, stage=stage, status=action, actor=actor, action=action, args=args,
                             result=result, request_id=request_id)

    def projects(self):
        out = []
        for e in self.events():
            if e['status'] == 'create_project':
                st = self.state(e['project'])
                out.append({'id': e['project'], 'title': st['title'], 'brand': st['brand'], 'stage': st['stage'],
                            'updated': st['updated']})
        return out

    # ------------------------------------------------------------------ the one write
    def act(self, pid: str | None, action: str, args: dict | None = None, actor='owner', request_id: str | None = None) -> dict:
        args = args or {}
        request_id = request_id or 'r-' + uuid.uuid4().hex[:16]
        with self.lock:
            for e in self.events(pid) if pid else self.events():
                if e['data'].get('request_id') == request_id:
                    return {'status': 'duplicate', 'event': e['seq'], 'result': e['data'].get('result'), 'action': action}
            fn = getattr(self, 'a_' + action, None)
            if fn is None:
                raise Refused(f'unknown action {action}')
            if action != 'create_project':
                if not pid or not any(e['status'] == 'create_project' for e in self.events(pid)):
                    raise Refused(f'no project {pid!r}')
            if action.startswith('cp_'):
                args = {**args, '_rid': request_id}         # nested decisions get request ids derived from this one
            stage, result = fn(pid, args, actor)
            pid = result.pop('_pid', pid)
            seq = self._emit(pid, stage, action, actor, request_id, args, result)
            return {'status': 'recorded', 'event': seq, 'result': result, 'action': action, 'project': pid}

    # ------------------------------------------------------------------ A. project
    def a_create_project(self, _pid, a, actor):
        brand = a.get('brand')
        title = (a.get('title') or '').strip()
        idea = (a.get('idea') or '').strip()
        if not idea: raise Refused('Write the idea first')
        if not title: raise Refused('Give the video a short title')
        if brand not in BRANDS: raise Refused('Choose a brand: Time Keeper or Diabetes History')
        pid = a.get('id') or _slug(title)
        base, n = pid, 2
        while any(e['status'] == 'create_project' for e in self.events(pid)):
            pid = f'{base}-{n}'; n += 1
        prof = self.profile(brand)
        ident = identity(brand, prof)
        self.pdir(pid).mkdir(parents=True, exist_ok=True)
        return 'project', {'_pid': pid, 'title': title, 'idea': idea, 'brand': brand, 'identity': ident}

    def profile(self, brand) -> dict:
        p = ROOT / BRANDS[brand]['profile']
        d = yaml.safe_load(p.read_text(encoding='utf-8'))
        d['_sha'] = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        return d

    def a_set_identity(self, pid, a, actor):
        st = self.state(pid)
        want = a.get('profile')
        prof = self.profile(st['brand'])
        if want != prof['id']:
            raise Refused(f'{want} is not a {BRANDS[st["brand"]]["name"]} profile; this project can only use {prof["id"]}')
        return 'project', {'identity': identity(st['brand'], prof)}

    def a_set_voice(self, pid, a, actor):
        """Choose the final-voice profile. Recorded with its real status: a voice approved for another film, or one
        that needs a per-film authorization, is selected but NOT usable until the owner authorizes it."""
        st = self.state(pid)
        prof = self.profile(st['brand'])
        name = a.get('voice')
        v = (prof.get('voice', {}).get('voices') or {}).get(name)
        if v is None:
            raise Refused(f'{name} is not a {BRANDS[st["brand"]]["name"]} voice')
        status, why = 'usable', ''
        if v.get('requires_authorization'):
            status, why = 'needs_authorization', 'this voice needs a per-film authorization recorded by the owner'
        elif v.get('approved_for') and pid not in v['approved_for']:
            status, why = 'needs_authorization', f'approved for {", ".join(v["approved_for"])} only; the owner must approve it for this film'
        if v.get('status') not in ('approved', 'approved_workflow', 'restricted'):
            status, why = 'not_approved', f'voice status is {v.get("status")}'
        voice = {'name': name, 'provider': v.get('provider'), 'voice_id': v.get('voice_id'), 'model': v.get('model'),
                 'settings': v.get('settings'), 'seed': v.get('seed'), 'output_format': v.get('output_format'),
                 'status': status, 'why': why, 'draft': prof['voice'].get('draft')}
        return 'project', {'voice': voice}

    def a_research(self, pid, a, actor):
        data = a.get('data')
        if not data or not data.get('claims'):
            raise Refused('research needs claims with sources')
        for c in data['claims']:
            if c.get('status') in ('verified', 'attributed') and not c.get('sources'):
                raise Refused(f'claim {c.get("id")} is {c["status"]} but has no source')
        rel = self.put(pid, json.dumps(data, ensure_ascii=False, indent=1).encode(), 'json')
        counts = {s: sum(1 for c in data['claims'] if c.get('status') == s) for s in ('verified', 'attributed', 'avoid', 'disputed')}
        return 'research', {'file': rel, 'counts': counts}

    def a_research_decision(self, pid, a, actor):
        d = a.get('decision')
        if d not in ('approved', 'changes_requested'):
            raise Refused('decision must be approved or changes_requested')
        st = self.state(pid)
        if not st['research']:
            raise Refused('no research to decide on')
        if st['research']['status'] != 'waiting':
            raise Refused(f'this research is already {st["research"]["status"]}; save new research to decide again')
        return 'research', {'decision': d, 'note': a.get('note', ''), 'file': st['research']['file']}

    # ------------------------------------------------------------------ B. script
    def a_script_version(self, pid, a, actor):
        st = self.state(pid)
        lines = a.get('lines') or []
        if not lines or any(not l.get('id') or not (l.get('text') or '').strip() for l in lines):
            raise Refused('a script version needs lines with an id and text')
        if len({l['id'] for l in lines}) != len(lines):
            raise Refused('line ids must be unique')
        lines = [{'id': l['id'], 'text': l['text'].strip(), **({'role': l['role']} if l.get('role') else {})} for l in lines]
        return 'script', self._new_version(pid, st, lines, a.get('note', ''), a.get('author', actor), a.get('parent'))

    def _new_version(self, pid, st, lines, note, author, parent=None, origin=None):
        earlier = [{**self._version_lines(pid, v), 'status': v['status']} for v in st['scripts']]
        found = checks.check_version(lines, self.research(pid), earlier)
        v = len(st['scripts']) + 1
        rel = self.put(pid, json.dumps({'v': v, 'lines': lines}, ensure_ascii=False, indent=1).encode(), 'json')
        parent = parent or (st['scripts'][-1]['v'] if st['scripts'] else None)
        diff = checks.word_diff(self._version_lines(pid, st['scripts'][parent - 1])['lines'], lines) if parent else []
        return {'v': v, 'file': rel, 'parent': parent, 'note': note, 'author': author, 'checks': found, 'diff': diff,
                **({'origin': origin} if origin else {})}

    def _version_lines(self, pid, sv) -> dict:
        return self.read_json(pid, sv['file'])

    def research(self, pid):
        st = self.state(pid)
        return self.read_json(pid, st['research']['file']) if st.get('research') else None

    def a_script_decision(self, pid, a, actor):
        st = self.state(pid)
        v, d = a.get('v'), a.get('decision')
        sv = next((s for s in st['scripts'] if s['v'] == v), None)
        if sv is None:
            raise Refused(f'no script version {v}')
        if d not in ('approved', 'rejected', 'changes_requested'):
            raise Refused('decision must be approved, rejected or changes_requested')
        if sv['status'] in ('approved', 'rejected'):
            raise Refused(f'v{v} is already {sv["status"]}; make a new version to change it')
        if sv['status'] == 'superseded':
            raise Refused(f'v{v} was replaced by v{st["scripts"][-1]["v"]}; decide on the latest version')
        if d == 'approved':
            crit = [c for c in sv['checks'] if c['severity'] == 'critical']
            if crit and not a.get('override'):
                raise Refused(f'v{v} has {len(crit)} critical finding(s): {crit[0]["detail"]}')
            note = (a.get('note') or '').strip()
            if crit and (len(note) < 12 or len([w for w in note.split() if len(w) >= 2]) < 3 or len(set(note.replace(' ', ''))) < 5):
                raise Refused('to approve over a critical finding, write in a sentence why the check is wrong here (kept with the version)')
            open_flags = [f for f in st['flags'] if f['v'] == v and f['status'] == 'open']
            if open_flags:
                raise Refused(f'v{v} has {len(open_flags)} open correction request(s)')
        return 'script', {'v': v, 'decision': d, 'note': a.get('note', ''), 'override': bool(a.get('override'))}

    def a_flag_word(self, pid, a, actor):
        """Highlight one word of a script version, say what is wrong and ask for a correction."""
        st = self.state(pid)
        v, lid, wi = a.get('v'), a.get('line'), a.get('wi')
        sv = next((s for s in st['scripts'] if s['v'] == v), None)
        if sv is None:
            raise Refused(f'no script version {v}')
        line = next((l for l in self._version_lines(pid, sv)['lines'] if l['id'] == lid), None)
        if line is None:
            raise Refused(f'no line {lid} in v{v}')
        ws = checks.words(line['text'])
        if not isinstance(wi, int) or not 0 <= wi < len(ws):
            raise Refused('word index out of range')
        if a.get('kind') not in FLAG_KINDS:
            raise Refused(f'kind must be one of {sorted(FLAG_KINDS)}')
        if any(f['v'] == v and f['line'] == lid and f['wi'] == wi and f['status'] == 'open' for f in st['flags']):
            raise Refused('this word already has an open correction request')
        fid = f'f{len(st["flags"]) + 1}'
        return 'script', {'flag': fid, 'v': v, 'line': lid, 'wi': wi, 'word': ws[wi], 'kind': a['kind'],
                          'note': a.get('note', ''), 'replacement': a.get('replacement', '')}

    def a_apply_correction(self, pid, a, actor):
        """Make a new version in which ONLY the flagged word changes. Earlier versions stay as they are."""
        st = self.state(pid)
        f = next((x for x in st['flags'] if x['flag'] == a.get('flag')), None)
        if f is None or f['status'] != 'open':
            raise Refused('no open correction request with that id')
        new_word = (a.get('replacement') or f.get('replacement') or '').strip()
        if not new_word or ' ' in new_word and len(new_word.split()) > 4:
            raise Refused('give the corrected word (up to four words)')
        latest = st['scripts'][-1]
        base = self._version_lines(pid, latest)['lines']
        line = next((l for l in base if l['id'] == f['line']), None)
        spans = [m.span() for m in checks.WORD.finditer(line['text'])] if line else []
        if not line or f['wi'] >= len(spans) or line['text'][slice(*spans[f['wi']])] != f['word']:
            raise Refused(f'the word «{f["word"]}» is no longer at that place in v{latest["v"]}; flag it again on the latest version')
        s, e = spans[f['wi']]
        lines = [dict(l) for l in base]
        for l in lines:
            if l['id'] == f['line']:
                l['text'] = l['text'][:s] + new_word + l['text'][e:]
        diff = checks.word_diff(base, lines)
        if len(diff) != 1 or diff[0]['line'] != f['line'] or diff[0]['old'] != f['word'].strip() and f['word'] not in diff[0]['old']:
            raise Refused(f'the correction would change more than the flagged word: {diff}')
        out = self._new_version(pid, st, lines, f'correction {f["flag"]}: «{f["word"]}» → «{new_word}»', actor,
                                parent=latest['v'], origin={'flag': f['flag']})
        out.update({'flag': f['flag'], 'replacement': new_word})
        return 'script', out

    def a_dismiss_flag(self, pid, a, actor):
        st = self.state(pid)
        f = next((x for x in st['flags'] if x['flag'] == a.get('flag')), None)
        if f is None or f['status'] != 'open':
            raise Refused('no open correction request with that id')
        return 'script', {'flag': f['flag'], 'note': a.get('note', '')}

    # ------------------------------------------------------------------ C. hooks
    def a_hooks(self, pid, a, actor):
        opts = a.get('options') or []
        if not 3 <= len(opts) <= 4:
            raise Refused('give 3 or 4 hooks')
        res = self.research(pid)
        for o in opts:
            for k in ('id', 'type', 'spoken', 'on_screen', 'visual'):
                if not o.get(k):
                    raise Refused(f'hook {o.get("id")} needs {k}')
            o['checks'] = hook_checks(o, res)
        rec = a.get('recommended')
        if rec not in [o['id'] for o in opts] or not a.get('reasons'):
            raise Refused('recommend one of the hooks and say why')
        set_n = len(self.state(pid)['hooks']['sets']) + 1
        return 'hook', {'set': set_n, 'options': opts, 'recommended': rec, 'reasons': a['reasons'], 'author': a.get('author', actor)}

    def a_hook_still(self, pid, a, actor):          # the opening frame of a hook, rendered by the engine (system)
        return 'hook', {'hook': a['hook'], 'still': a['still']}

    def a_hook_select(self, pid, a, actor):
        st = self.state(pid)
        hs = st['hooks']
        if not hs['options']:
            raise Refused('no hooks to choose from')
        h = next((o for o in hs['options'] if o['id'] == a.get('hook')), None)
        if h is None:
            raise Refused('unknown hook')
        # the chosen hook becomes the first line of a NEW script version (to be approved like any other)
        approved = [s for s in st['scripts'] if s['status'] == 'approved']
        out = {'hook': h['id'], 'reason': a.get('note', '')}
        if approved:
            base = self._version_lines(pid, approved[-1])['lines']
            lines = [{'id': 'h', 'text': h['spoken'], 'role': 'hook'}] + [l for l in base if l.get('role') != 'hook']
            out['script'] = self._new_version(pid, st, lines, f'hook {h["id"]} as the opening line', 'system',
                                              parent=approved[-1]['v'], origin={'hook': h['id']})
        return 'hook', out

    def a_hook_delivery(self, pid, a, actor):
        st = self.state(pid)
        if not st['hooks']['selected']:
            raise Refused('select a hook first')
        if a.get('decision') not in ('delivered', 'not_delivered'):
            raise Refused('decision must be delivered or not_delivered')
        if st['hooks']['delivery']:
            raise Refused(f'already decided ({st["hooks"]["delivery"]["decision"]}); choose the hook again to decide again')
        if a['decision'] == 'delivered' and not a.get('line'):
            raise Refused('say which line pays off the hook')
        return 'hook', {'hook': st['hooks']['selected'], 'decision': a['decision'], 'line': a.get('line'), 'note': a.get('note', '')}

    # ------------------------------------------------------------------ D. voice (jobs live in voice.py)
    def a_voice_take(self, pid, a, actor):            # recorded by the job runner (actor 'system')
        return 'voice', a

    def a_voice_flag(self, pid, a, actor):
        st = self.state(pid)
        t = st['voice']['takes'].get(a.get('take'))
        if t is None:
            raise Refused('unknown take')
        wi = a.get('wi')
        if not isinstance(wi, int) or not 0 <= wi < len(t['words']):
            raise Refused('word index out of range')
        if a.get('kind') not in VFLAG_KINDS:
            raise Refused(f'kind must be one of {sorted(VFLAG_KINDS)}')
        if not a.get('played'):
            raise Refused('play the word before flagging it')
        fid = f'vf{len(st["voice"]["flags"]) + 1}'
        return 'voice', {'vflag': fid, 'take': t['id'], 'line': t['line'], 'wi': wi, 'word': t['words'][wi]['w'],
                         'kind': a['kind'], 'note': a.get('note', ''), 'respell': a.get('respell', '')}

    def a_voice_fix(self, pid, a, actor):
        """Turn a flagged word into a pronunciation rule for this project (draft voice) and ask for a new take of
        that line only. The rule is recorded; the job runner makes the take."""
        st = self.state(pid)
        f = next((x for x in st['voice']['flags'] if x['vflag'] == a.get('vflag')), None)
        if f is None or f['status'] not in ('open', 'fix_no_effect'):
            raise Refused('no open voice flag with that id')
        respell = (a.get('respell') or f.get('respell') or '').strip()
        if not respell:
            raise Refused('give the spelling the draft voice should read (for example with vowels)')
        return 'voice', {'vflag': f['vflag'], 'line': f['line'], 'word': f['word'], 'respell': respell,
                         'rule': {'id': f'p-{pid}-{f["vflag"]}-{len(st["voice"]["rules"]) + 1}', 'scope': f'project:{pid}', 'surface': checks.bare(f['word']),
                                  'status': 'approved', 'providers': {'gtts': {'mode': 'spoken', 'spoken': respell, 'article_ok': True}},
                                  'lines': [f['line']]}}

    def a_take_decision(self, pid, a, actor):
        st = self.state(pid)
        t = st['voice']['takes'].get(a.get('take'))
        if t is None:
            raise Refused('unknown take')
        d = a.get('decision')
        if d not in ('approved', 'rejected'):
            raise Refused('decision must be approved or rejected')
        if t['status'] in ('approved', 'rejected'):
            raise Refused(f'this take is already {t["status"]}')
        pb = a.get('playback') or {}
        heard = _heard(pb, t['seconds'])
        if heard < 0.8 * t['seconds']:
            raise Refused(f'listen to the take before deciding: {heard:.1f} s of {t["seconds"]:.1f} s heard '
                          '(skipping, replaying the same part or muted playback does not count)')
        f = next((x for x in st['voice']['flags'] if t.get('reason') == f'correction {x["vflag"]}'), None)
        if f and f['wi'] < len(t['words']):                     # a re-take after a fix: the fixed word itself must be heard
            w = t['words'][f['wi']]
            if _overlap(pb.get('covered'), w['s'], w['e']) < 0.6 * (w['e'] - w['s']):
                raise Refused(f'listen to the fixed word «{w["w"]}» ({w["s"]:.1f}–{w["e"]:.1f} s) before deciding on this take')
        if d == 'approved' and t.get('same_audio_as') and st['voice']['takes'].get(t['same_audio_as'], {}).get('status') == 'rejected':
            raise Refused('this take is the same audio as a take you rejected')
        return 'voice', {'take': t['id'], 'line': t['line'], 'decision': d, 'note': a.get('note', ''), 'playback': pb}

    # ------------------------------------------------------------------ E/F. art
    def a_art_brief(self, pid, a, actor):
        b = a.get('brief') or {}
        if not b.get('scenes'):
            raise Refused('an art brief needs scenes')
        rel = self.put(pid, json.dumps(b, ensure_ascii=False, indent=1).encode(), 'json')
        return 'art', {'file': rel, 'scenes': list(b['scenes'])}

    def a_art_concepts(self, pid, a, actor):          # recorded by the job runner
        return 'art', a

    def a_art_revision(self, pid, a, actor):          # recorded by the job runner
        return 'art', a

    def a_art_select(self, pid, a, actor):
        c = self._concept(pid, a)
        if c['support'] != 'rendered':
            raise Refused(f'this concept has no image to choose ({c["support"]})')
        if c['versions'][-1].get('status') in ('rejected', 'withdrawn'):
            raise Refused(f'the latest version of this concept was {c["versions"][-1]["status"]}; request a revision first')
        return 'art', {'scene': c['scene'], 'concept': c['id']}

    def a_art_modify(self, pid, a, actor):
        c = self._concept(pid, a)
        ch = a.get('changes') or {}
        if not ch and not a.get('note'):
            raise Refused('say what to change')
        if any(q['concept'] == c['id'] and q['status'] in ('open', 'waiting_operator') for q in self.state(pid)['art']['requests']):
            raise Refused('a change request for this concept is already open')
        if ch:
            from . import art
            last = c['versions'][-1]
            eff = art.effective_changes(c['technique'], last.get('params', c['params']), last.get('theme', c['theme']))
            dead = [f'{k}:{v}' for k, v in ch.items() if f'{k}:{v}' not in eff]
            if dead:
                raise Refused(f'this {c["technique"]} drawing would not change with: '
                              + ', '.join(art.CHANGE_CHIPS.get(d, d) for d in dead) + ' (say it in the note for the art operator instead)')
        return 'art', {'scene': c['scene'], 'concept': c['id'], 'changes': ch, 'note': a.get('note', ''),
                       'from_version': c['versions'][-1]['v'], 'needs_operator': not ch}

    def a_art_operator_revision(self, pid, a, actor):
        """The art operator answers a free-text request with new parameters (the job renders them)."""
        c = self._concept(pid, a)
        if not a.get('params'):
            raise Refused('give the new parameters')
        return 'art', {'concept': c['id'], 'scene': c['scene'], 'params': a['params'], 'theme': a.get('theme') or c['theme'], 'note': a.get('note', '')}

    def a_art_decision(self, pid, a, actor):
        c = self._concept(pid, a)
        d, v = a.get('decision'), a.get('version')
        if d == 'approved' and c['support'] != 'rendered':
            raise Refused(f'this concept has no artwork to approve ({c["support"]})')
        if d not in ('approved', 'rejected', 'withdrawn'):
            raise Refused('decision must be approved, rejected or withdrawn')
        ver = next((x for x in c['versions'] if x['v'] == v), None)
        if ver is None:
            raise Refused(f'no version {v} of this concept')
        if d == 'withdrawn':
            if ver.get('status') != 'approved':
                raise Refused('only an approved version can be withdrawn')
            if not (a.get('note') or '').strip():
                raise Refused('say why the approval is withdrawn (kept in the history)')
        elif ver.get('status') in ('approved', 'rejected', 'withdrawn'):
            raise Refused(f'version {v} is already {ver["status"]}' + ('; withdraw the approval first' if ver.get('status') == 'approved' else ''))
        st = self.state(pid)
        cur = st['art']['approved'].get(c['scene'])
        if d == 'approved' and cur and not (cur['concept'] == c['id'] and v > cur['version']):
            raise Refused(f'scene {c["scene"]} already has approved art; withdraw that approval first to approve another')
        return 'art', {'scene': c['scene'], 'concept': c['id'], 'version': v, 'decision': d, 'note': a.get('note', '')}

    def _concept(self, pid, a):
        st = self.state(pid)
        c = st['art']['concepts'].get(a.get('concept'))
        if c is None:
            raise Refused('unknown concept')
        return c

    # ------------------------------------------------------------------ G. storyboard and draft
    def a_storyboard(self, pid, a, actor):            # recorded by storyboard.build()
        return 'storyboard', a

    def a_storyboard_decision(self, pid, a, actor):
        """The owner approves the storyboard as a whole: every scene's visual, including the brief's defaults."""
        st = self.state(pid)
        if not st['storyboards']:
            raise Refused('build a storyboard first')
        sb = st['storyboards'][-1]
        if a.get('v') != sb['v']:
            raise Refused(f'decide on the latest storyboard (v{sb["v"]})')
        if a.get('decision') not in ('approved', 'changes_requested'):
            raise Refused('decision must be approved or changes_requested')
        if sb.get('decision'):
            raise Refused(f'storyboard v{sb["v"]} is already {sb["decision"]}; build a new one to decide again')
        if a['decision'] == 'approved' and any('stale' in str(x['status']['voice']) or x['status']['voice'] == 'missing' for x in sb['scenes']):
            raise Refused('some scenes have no voice for their current text; make the draft read first')
        return 'storyboard', {'v': sb['v'], 'decision': a['decision'], 'note': a.get('note', ''),
                              'unreviewed': [x['id'] for x in sb['scenes'] if x['status']['art'] != 'approved']}

    def a_authorize_voice(self, pid, a, actor):
        """The owner authorizes the chosen final voice for THIS film (an owner decision; nothing is generated)."""
        st = self.state(pid)
        v = st['voice_profile']
        if not v: raise Refused('choose the final voice first')
        if v['status'] == 'usable': raise Refused('this voice is already usable for this film')
        if len((a.get('note') or '').strip()) < 8: raise Refused('write who authorizes it and why (kept in the history)')
        return 'gate', {'voice': v['name'], 'note': a['note']}

    def a_term_decision(self, pid, a, actor):
        """How the FINAL voice receives a name: Latin spelling (as Time Keeper sends names) or the Arabic as written."""
        if a.get('decision') not in ('latin', 'arabic'): raise Refused('decision must be latin or arabic')
        terms = [t['ar'] for t in (self.research(pid) or {}).get('terms', [])]
        if a.get('surface') not in terms: raise Refused('unknown term')
        return 'gate', {'surface': a['surface'], 'decision': a['decision']}

    def a_set_budget(self, pid, a, actor):
        n = a.get('characters')
        if not isinstance(n, int) or n <= 0 or n > 200000: raise Refused('give the budget in characters (a positive number)')
        from ..ledger import Ledger
        Ledger(self.var / 'ledger.sqlite').set_budget(pid, 'elevenlabs', n, by=actor)
        return 'gate', {'characters': n}

    def a_render(self, pid, a, actor):                # recorded by the job runner
        return 'draft', a

    def a_render_decision(self, pid, a, actor):
        st = self.state(pid)
        r = next((x for x in st['renders'] if x['id'] == a.get('render')), None)
        if r is None or r.get('state') != 'ok':
            raise Refused('no finished render with that id')
        if a.get('decision') not in ('approved_as_draft', 'changes_requested'):
            raise Refused('decision must be approved_as_draft or changes_requested')
        if r.get('decision'):
            raise Refused(f'this draft is already {r["decision"]}; render a new one to decide again')
        pb = a.get('playback') or {}
        heard = _heard(pb, r['seconds'])
        if heard < 0.8 * r['seconds']:
            raise Refused(f'watch the draft before deciding: {heard:.0f} s of {r["seconds"]:.0f} s watched '
                          '(skipping, replaying the same part or muted playback does not count)')
        return 'draft', {'render': r['id'], 'decision': a['decision'], 'note': a.get('note', ''), 'playback': pb}

    # ------------------------------------------------------------------ H. review
    def a_review(self, pid, a, actor):                # recorded by the job runner
        return 'review', a

    def a_finding_decision(self, pid, a, actor):
        st = self.state(pid)
        f = st['review']['findings'].get(a.get('finding'))
        if f is None:
            raise Refused('unknown finding')
        if a.get('decision') not in ('accepted', 'dismissed'):
            raise Refused('decision must be accepted or dismissed')
        if f['decision']:
            raise Refused(f'this finding is already {f["decision"]}')
        if a['decision'] == 'dismissed' and not (a.get('note') or '').strip():
            raise Refused('say why the finding is dismissed (kept in the review history)')
        out = {'finding': f['id'], 'decision': a['decision'], 'note': a.get('note', '')}
        if a['decision'] == 'accepted':
            out['task'] = {'id': 'fix-' + f['id'], 'scene': f.get('scene'), 'what': f['recommendation'], 'stage': f.get('fix_stage', 'art')}
        return 'review', out

    def a_fix_done(self, pid, a, actor):
        st = self.state(pid)
        t = next((x for x in st['fix_tasks'] if x['id'] == a.get('task')), None)
        if t is None or t['status'] != 'open':
            raise Refused('no open correction task with that id')
        return 'review', {'task': t['id'], 'note': a.get('note', '')}

    # ------------------------------------------------------------------ J. final gate
    def a_gate_plan(self, pid, a, actor):             # recorded by gate.plan()
        return 'gate', a

    def a_gate_authorize(self, pid, a, actor):
        """The owner's authorization is only possible when every condition holds. In this development workspace
        the paid gateway is disabled, so even a complete authorization cannot start a paid run from here."""
        from .gate import authorization_blockers
        st = self.state(pid)
        bl = authorization_blockers(self, pid, st, a)
        if bl:
            raise Refused('not authorized: ' + '; '.join(bl))
        return 'gate', {'plan': st['gate']['plan']['hash'], 'by': actor}

    def a_final_generate(self, pid, a, actor):
        raise Refused('paid generation cannot be started from the studio: the paid gateway is disabled in this '
                      'development workspace (VIDEO_DIRECTOR_PAID_ENABLED is not 1) and the studio has no route to it')

    # ------------------------------------------------------------------ job bookkeeping
    def a_job(self, pid, a, actor):                   # job started/finished/failed (system)
        return a.get('stage', 'project'), a

    # ================================================================== state
    def state(self, pid) -> dict:
        """The project rebuilt from its events. Cached until a new event, a new refusal or a change in the live jobs: a page
        refresh, the Co-Pilot's planning and a media request then share one replay instead of each doing its own."""
        import copy
        rf = self.root / pid / 'refusals.jsonl'
        key = (self.log.last_seq(kind='studio', project=pid), rf.stat().st_size if rf.exists() else 0, tuple(sorted(self.jobs)))
        cache = self.__dict__.setdefault('_state_cache', {})
        hit = cache.get(pid)
        if hit and hit[0] == key:
            return copy.deepcopy(hit[1])
        st = self._state(pid)
        cache[pid] = (key, copy.deepcopy(st))
        return st

    def _state(self, pid) -> dict:
        evs = self.events(pid)
        if not any(e['status'] == 'create_project' for e in evs):
            raise Refused(f'no project {pid!r}')
        st = {'id': pid, 'title': '', 'idea': '', 'brand': None, 'identity': None, 'voice_profile': None,
              'research': None, 'scripts': [], 'flags': [], 'hooks': {'sets': [], 'options': [], 'recommended': None,
              'reasons': '', 'selected': None, 'stills': {}, 'delivery': None},
              'voice': {'takes': {}, 'by_line': {}, 'flags': [], 'rules': [], 'narration_v': None},
              'art': {'concepts': {}, 'by_scene': {}, 'selected': {}, 'approved': {}, 'requests': []},
              'storyboards': [], 'renders': [], 'review': {'runs': [], 'findings': {}}, 'fix_tasks': [],
              'gate': {'plan': None, 'attempts': []}, 'jobs': [], 'history': [], 'updated': None, 'created': None,
              'copilot': _cp_empty()}
        for e in evs:
            d, r, act = e['data'].get('args') or {}, e['data'].get('result') or {}, e['status']
            st['updated'] = e['at']
            st['history'].append({'seq': e['seq'], 'at': e['at'], 'action': act, 'actor': e['actor'], 'stage': e['stage'],
                                  'summary': _summary(act, d, r)})
            if act.startswith('cp_'):
                _cp_fold(st, e)
            elif act == 'create_project':
                st.update(title=r['title'], idea=r['idea'], brand=r['brand'], identity=r['identity'], created=e['at'])
            elif act == 'set_identity':
                st['identity'] = r['identity']
            elif act == 'set_voice':
                st['voice_profile'] = r['voice']
                why = st['gate'].setdefault('voice_auth', {}).get(r['voice']['name'])
                if why:                                          # authorized earlier for this film: switching back keeps it
                    st['voice_profile'] = {**r['voice'], 'status': 'usable', 'why': why}
            elif act == 'research':
                st['research'] = {**r, 'status': 'waiting', 'at': e['at']}
            elif act == 'research_decision':
                st['research']['status'] = r['decision']; st['research']['note'] = r['note']
            elif act in ('script_version', 'apply_correction') or (act == 'hook_select' and r.get('script')):
                sv = r['script'] if act == 'hook_select' else r
                st['scripts'].append({**{k: sv[k] for k in ('v', 'file', 'parent', 'note', 'author', 'checks', 'diff')},
                                      'origin': sv.get('origin'), 'status': 'draft', 'at': e['at'], 'decided': None})
                if act == 'hook_select':
                    st['hooks']['selected'] = r['hook']; st['hooks']['delivery'] = None
                if act == 'apply_correction':
                    for f in st['flags']:
                        if f['flag'] == r['flag']: f.update(status='applied', applied_in=r['v'], replacement=r['replacement'])
            elif act == 'script_decision':
                for s in st['scripts']:
                    if s['v'] == r['v']: s.update(status=r['decision'], decided=e['at'], note_decision=r['note'], override=r.get('override', False))
            elif act == 'flag_word':
                st['flags'].append({**r, 'status': 'open', 'at': e['at']})
            elif act == 'dismiss_flag':
                for f in st['flags']:
                    if f['flag'] == r['flag']: f.update(status='dismissed', dismiss_note=r['note'])
            elif act == 'hooks':
                st['hooks']['sets'].append(r)
                st['hooks'].update(options=r['options'], recommended=r['recommended'], reasons=r['reasons'], selected=None)
            elif act == 'hook_still':
                st['hooks']['stills'][r['hook']] = r['still']
            elif act == 'hook_select':
                st['hooks']['selected'] = r['hook']; st['hooks']['delivery'] = None
            elif act == 'hook_delivery':
                st['hooks']['delivery'] = r
            elif act == 'voice_take':
                t = {**r, 'status': 'candidate', 'at': e['at']}
                st['voice']['takes'][r['id']] = t
                st['voice']['by_line'].setdefault(r['line'], []).append(r['id'])
                st['voice']['narration_v'] = r.get('script_v', st['voice']['narration_v'])
            elif act == 'voice_flag':
                st['voice']['flags'].append({**r, 'status': 'open', 'at': e['at']})
            elif act == 'voice_fix':
                st['voice']['rules'] = [x for x in st['voice']['rules'] if x['id'] != r['rule']['id']] + [r['rule']]
                for f in st['voice']['flags']:
                    if f['vflag'] == r['vflag']: f.update(status='fix_requested', respell=r['respell'])
            elif act == 'take_decision':
                st['voice']['takes'][r['take']].update(status=r['decision'], decided=e['at'])
            elif act == 'art_brief':
                st['art']['brief'] = r['file']
            elif act == 'art_concepts':
                for c in r['concepts']:
                    c = {**c, 'versions': [dict(v) for v in c.get('versions', [])]}
                    st['art']['concepts'][c['id']] = c
                    st['art']['by_scene'].setdefault(c['scene'], [])
                    if c['id'] not in st['art']['by_scene'][c['scene']]: st['art']['by_scene'][c['scene']].append(c['id'])
            elif act == 'art_select':
                st['art']['selected'][r['scene']] = r['concept']
            elif act == 'art_modify':
                st['art']['requests'].append({**r, 'status': 'waiting_operator' if r.get('needs_operator') else 'open', 'at': e['at'], 'seq': e['seq']})
            elif act == 'art_operator_revision':
                for q in st['art']['requests']:
                    if q['concept'] == r['concept'] and q['status'] == 'waiting_operator': q.update(status='open', answered=True)
            elif act == 'art_revision':
                c = st['art']['concepts'][r['concept']]
                c['versions'].append({**r['version']})
                for q in st['art']['requests']:
                    if q['concept'] == r['concept'] and q['status'] == 'open':
                        q.update(status='no_visible_change' if r['version'].get('no_visible_change') else
                                 'waiting_operator' if (q.get('note') or '').strip() and not q.get('answered') else 'done',
                                 version=r['version']['v'])   # an unanswered note still needs the operator; an answered one is done
            elif act == 'art_decision':
                c = st['art']['concepts'][r['concept']]
                prev = st['art']['approved'].get(r['scene'])
                for v in c['versions']:
                    if v['v'] == r['version']: v.update(status=r['decision'], decided=e['at'])
                if r['decision'] == 'approved':
                    if prev and prev['concept'] == r['concept']:          # a newer version of the approved art replaces it
                        for v in c['versions']:
                            if v['v'] == prev['version']: v.update(status='replaced', replaced_by=r['version'])
                    st['art']['approved'][r['scene']] = {'concept': r['concept'], 'version': r['version']}
                elif prev == {'concept': r['concept'], 'version': r['version']}:
                    st['art']['approved'].pop(r['scene'])
                if r['decision'] in ('rejected', 'withdrawn') and st['art']['selected'].get(r['scene']) == r['concept'] \
                        and (st['art']['approved'].get(r['scene']) or {}).get('concept') != r['concept']:
                    st['art']['selected'].pop(r['scene'])
            elif act == 'storyboard':
                st['storyboards'].append({**r, 'at': e['at']})
            elif act == 'storyboard_decision':
                for b in st['storyboards']:
                    if b['v'] == r['v']: b.update(decision=r['decision'], decision_note=r['note'])
            elif act == 'authorize_voice':
                if st['voice_profile'] and st['voice_profile']['name'] == r['voice']:
                    st['voice_profile'] = {**st['voice_profile'], 'status': 'usable', 'why': f'authorized for this film by the owner: {r["note"]}'}
                    st['gate'].setdefault('voice_auth', {})[r['voice']] = st['voice_profile']['why']
            elif act == 'term_decision':
                st['gate'].setdefault('terms', {})[r['surface']] = r['decision']
            elif act == 'set_budget':
                st['gate']['budget'] = r['characters']
            elif act == 'render':
                st['renders'] = [x for x in st['renders'] if x['id'] != r['id']] + [{**r, 'at': e['at']}]
            elif act == 'render_decision':
                for x in st['renders']:
                    if x['id'] == r['render']: x.update(decision=r['decision'], decision_note=r['note'])
            elif act == 'review':
                st['review']['runs'].append({k: r[k] for k in r if k != 'findings'} | {'at': e['at']})
                for f in r.get('findings', []):
                    st['review']['findings'][f['id']] = {**f, 'decision': None, 'run': r['id']}
            elif act == 'finding_decision':
                st['review']['findings'][r['finding']].update(decision=r['decision'], decision_note=r['note'], decided=e['at'])
                if r.get('task'):
                    st['fix_tasks'].append({**r['task'], 'status': 'open', 'finding': r['finding'], 'at': e['at']})
            elif act == 'fix_done':
                for t in st['fix_tasks']:
                    if t['id'] == r['task']: t.update(status='done', note=r['note'])
            elif act == 'gate_plan':
                st['gate']['plan'] = r
            elif act == 'gate_authorize':
                st['gate']['authorized'] = r
            elif act == 'job':
                prior = next((j for j in st['jobs'] if j['id'] == r['id']), {})
                st['jobs'] = [j for j in st['jobs'] if j['id'] != r['id']] + [{**prior, **r, 'at': e['at'], 'seq': e['seq']}]
                vf = (r.get('args') or prior.get('args') or {}).get('vflag')
                if r['state'] == 'finished' and vf and (r.get('out') or {}).get('no_effect'):
                    for f in st['voice']['flags']:
                        if f['vflag'] == vf: f['status'] = 'fix_no_effect'
        for s in st['scripts'][:-1]:                     # an older draft is superseded by any newer version
            if s['status'] == 'draft': s['status'] = 'superseded'
        # refused attempts at the final step are kept (every refusal is in refusals.jsonl)
        st['gate']['attempts'] = [x for x in self.refusals(pid) if x['action'] in ('gate_authorize', 'final_generate')]
        st['refusals'] = self.refusals(pid)[-50:]
        for j in st['jobs']:
            if j['state'] == 'running' and j['id'] not in self.jobs:
                j['state'] = 'interrupted'                 # the server stopped while it ran: resumable, never "done"
        if not any(j['kind'] == 'render' and j['state'] == 'running' for j in st['jobs']):
            for r in st['renders']:
                if r.get('state') == 'running': r['state'] = 'interrupted'
        st['voice']['lines'] = self._voice_lines(pid, st)
        st['stage'], st['steps'] = progress(st)
        return st

    def _voice_lines(self, pid, st) -> dict:
        """For every line of the latest APPROVED script: which take is current and its state. A take only counts for
        a line if it was made from that line's exact current text; otherwise the line is 'stale' (the script changed
        after it was voiced) or 'missing'."""
        ap = [x for x in st['scripts'] if x['status'] == 'approved']
        if not ap: return {}
        tk, out = st['voice']['takes'], {}
        for ln in self.read_json(pid, ap[-1]['file'])['lines']:
            ids = st['voice']['by_line'].get(ln['id'], [])
            match = [tk[i] for i in ids if tk[i]['text'] == ln['text']]
            cur = (next((t for t in reversed(match) if t['status'] == 'approved'), None) or (match[-1] if match else None))
            out[ln['id']] = {'take': cur and cur['id'], 'text': ln['text'],
                             'status': ('missing' if not ids else 'stale' if not match else cur['status']),
                             'stale_take': ids[-1] if ids and not match else None}
        return out

    # ------------------------------------------------------------------ refusals are history too
    def refuse_log(self, pid, action, args, reason, actor):
        p = self.root / pid / 'refusals.jsonl' if pid and (self.root / pid).exists() else self.root / 'refusals.jsonl'
        with open(p, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'action': action,
                                'reason': reason, 'actor': actor}, ensure_ascii=False) + '\n')

    def refusals(self, pid):
        p = self.root / pid / 'refusals.jsonl'
        if not p.exists(): return []
        return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]


# ====================================================================== helpers
def identity(brand: str, prof: dict) -> dict:
    """What a project of this brand loads: its own palette, themes, end card, rules and techniques, nothing else."""
    style = {}
    if brand == 'timekeeper':
        sp = ROOT / 'director/studio/assets/tk-style.json'
        style = json.loads(sp.read_text(encoding='utf-8'))
    return {'brand': brand, 'brand_name': BRANDS[brand]['name'], 'profile': prof['id'], 'profile_version': prof.get('version'),
            'profile_status': prof.get('status'), 'profile_sha': prof.get('_sha'), 'look': prof.get('look'),
            'rules': prof.get('rules'), 'art': prof.get('art'), 'themes': list((style.get('themes') or {}).keys()),
            'palette': {k: v['bg'] for k, v in (style.get('themes') or {}).items()},
            'endcard': (prof.get('look') or {}).get('endcard'),
            'voices': {k: {'provider': v.get('provider'), 'status': v.get('status'), 'approved_for': v.get('approved_for')}
                       for k, v in ((prof.get('voice') or {}).get('voices') or {}).items()},
            'draft_voice': (prof.get('voice') or {}).get('draft'),
            'library_scopes': (prof.get('voice') or {}).get('library_scopes')}


def hook_checks(o: dict, research: dict | None) -> list[dict]:
    out = []
    n_sp, n_os = len(o['spoken'].split()), len(o['on_screen'].split())
    if not 6 <= n_sp <= 14: out.append({'code': 'SPOKEN_LENGTH', 'severity': 'minor', 'detail': f'spoken line has {n_sp} words (6–14)'})
    if not 3 <= n_os <= 7: out.append({'code': 'ON_SCREEN_LENGTH', 'severity': 'minor', 'detail': f'on-screen text has {n_os} words (3–7)'})
    out += [c for c in checks.check_version([{'id': 'hook', 'text': o['spoken']}], research, []) if c['code'] == 'CLAIM_UNSUPPORTED']
    return out


def _summary(act, a, r) -> str:
    return {
        'create_project': lambda: f'created «{r.get("title")}» ({r.get("brand")})',
        'set_voice': lambda: f'final voice {r["voice"]["name"]}: {r["voice"]["status"]}',
        'set_identity': lambda: f'identity {r["identity"]["profile"]}',
        'research': lambda: f'research saved ({r["counts"]})',
        'research_decision': lambda: f'research {r["decision"]}',
        'script_version': lambda: f'script v{r["v"]} ({len(r["checks"])} check findings)',
        'apply_correction': lambda: f'correction {r["flag"]} → v{r["v"]}',
        'script_decision': lambda: f'script v{r["v"]} {r["decision"]}',
        'flag_word': lambda: f'flagged «{r["word"]}» in {r["line"]} (v{r["v"]}): {r["kind"]}',
        'dismiss_flag': lambda: f'dismissed {r["flag"]}',
        'hooks': lambda: f'{len(r["options"])} hooks, recommended {r["recommended"]}',
        'hook_select': lambda: f'hook {r["hook"]} selected' + (f' → script v{r["script"]["v"]}' if r.get('script') else ''),
        'hook_delivery': lambda: f'hook {r["hook"]}: {r["decision"]}',
        'hook_still': lambda: f'opening frames drawn for hook {r["hook"]}',
        'voice_take': lambda: f'draft take for {r["line"]} ({r["seconds"]} s)',
        'voice_flag': lambda: f'voice flag «{r["word"]}» in {r["line"]}: {r["kind"]}',
        'voice_fix': lambda: f'pronunciation rule «{r["word"]}» → «{r["respell"]}» for {r["line"]}',
        'take_decision': lambda: f'take {r["take"]} ({r["line"]}) {r["decision"]}',
        'art_brief': lambda: f'art brief for {len(r["scenes"])} scenes',
        'art_concepts': lambda: f'{len(r["concepts"])} art concepts for {r.get("scene")}',
        'art_select': lambda: f'concept {r["concept"]} selected for {r["scene"]} (not approved)',
        'art_modify': lambda: f'changes requested on {r["concept"]}' + (' (waiting for the art operator)' if r.get('needs_operator') else ''),
        'art_operator_revision': lambda: f'art operator answered the request on {r["concept"]}',
        'art_revision': lambda: f'{r["concept"]} v{r["version"]["v"]} made',
        'art_decision': lambda: f'{r["concept"]} v{r["version"]} {r["decision"]}',
        'storyboard': lambda: f'storyboard v{r["v"]} ({len(r["scenes"])} scenes, {r["seconds"]} s)',
        'render': lambda: f'render {r["id"]}: {r["state"]}',
        'render_decision': lambda: f'draft {r["render"]}: {r["decision"]}',
        'review': lambda: f'review {r["id"]}: {len(r.get("findings", []))} findings',
        'finding_decision': lambda: f'finding {r["finding"]} {r["decision"]}',
        'fix_done': lambda: f'correction task {r["task"]} done',
        'gate_plan': lambda: f'final plan {r["hash"][:10]}: {r["chars_total"]} characters',
        'gate_authorize': lambda: 'final plan authorized',
        'storyboard_decision': lambda: f'storyboard v{r["v"]} {r["decision"]}' + (f' ({len(r["unreviewed"])} scenes on the brief default)' if r.get('unreviewed') else ''),
        'authorize_voice': lambda: f'final voice {r["voice"]} authorized for this film',
        'term_decision': lambda: f'final voice gets «{r["surface"]}» as {r["decision"]}',
        'set_budget': lambda: f'ElevenLabs budget set to {r["characters"]} characters',
        'job': lambda: f'{r["what"]}: {r["state"]}',
    }.get(act, lambda: _cp_summary(act, a, r))()


def _cp_summary(act, a, r) -> str:
    try:
        return {
            'cp_mode': lambda: f'mode: {r["mode"]}',
            'cp_settings': lambda: 'settings: ' + ', '.join(f'{k}={v}' for k, v in r.items()),
            'cp_control': lambda: f'Co-Pilot {r["op"]}' + (f' {r["key"]}' if r.get('key') else ''),
            'cp_ai_budget': lambda: f'AI usage budget set to ${r["usd"]:.2f}',
            'cp_ai_call': lambda: f'AI {r["role"]} ({r["worker"]}): {r["kind"]} ' + ('ok' if r['ok'] else 'failed') + (f', ${r["cost_usd"]:.4f}' if r.get('cost_usd') else ''),
            'cp_direction': lambda: f'story direction v{r["v"]}',
            'cp_check': lambda: f'{r["kind"]} check of {r["target"]} {r["ref"]} by {r.get("by", "?")}',
            'cp_ready': lambda: f'{r["gate"]} ready for the owner',
            'cp_stage': lambda: f'{r["stage"]}: {r.get("task", "")} {r.get("state", "")}'.strip(),
            'cp_gate': lambda: f'{r["gate"]} {r["decision"]} (version {r["ref"]})',
            'cp_hook': lambda: f'hook {r["hook"]} chosen → script v{r["v"]}',
            'cp_line_edit': lambda: f'owner edited {r["line"]} → script v{r["v"]}',
            'cp_pron': lambda: (f'pronunciation «{r["word"]}» → «{r["respell"]}» ({r["source"]})' if r['op'] == 'add' else f'pronunciation {r["id"]} {r["decision"]}'),
            'cp_voice_adjust': lambda: f'speed {r["speed"]}, pauses {r["pause_before"]}/{r["pause_after"]} s for {r["line"]} (local processing)',
            'cp_voice_mix': lambda: f'play-all narration ({len(r["segments"])} lines)',
            'cp_style': lambda: f'{len(r["directions"])} style boards, recommended {r["recommended"]}',
            'cp_asset': lambda: f'asset {r["id"]}: {r["op"]}',
            'cp_asset_needs': lambda: f'{len(r["needs"])} pictures needed',
            'cp_exception': lambda: f'needs your decision: {r["title"]}',
            'cp_exception_decision': lambda: f'exception {r["id"]}: {r["decision"]}',
            'cp_scene': lambda: f'scene {r["scene"]} v{r["n"]} (round {r["round"]}): {r["status"]}',
            'cp_film': lambda: f'film v{r["n"]}: {r["state"]}',
            'cp_comment': lambda: f'comment at {r["t"]} s on {r["scene"]}',
            'cp_task': lambda: f'task {r["id"]}: {r.get("status")}',
            'cp_finding': lambda: f'finding {r["finding"]} explained by the owner',
            'cp_script_meta': lambda: f'script v{r["v"]} notes',
        }[act]()
    except Exception:
        return act


def progress(st: dict):
    """Each step's state from decisions only (never from files existing)."""
    S = {}
    rs = st['research']
    S['research'] = ('approved' if rs and rs['status'] == 'approved' else 'waiting_review' if rs else 'not_started')
    sc = st['scripts']
    appr = [s for s in sc if s['status'] == 'approved']
    latest = sc[-1] if sc else None
    S['script'] = ('approved' if latest and latest['status'] == 'approved' else 'waiting_review' if latest else 'not_started')
    h = st['hooks']
    S['hook'] = ('approved' if h['selected'] and h['delivery'] and h['delivery']['decision'] == 'delivered' else
                 'waiting_review' if h['options'] else 'not_started')
    tk = st['voice']['takes']
    vl = st['voice'].get('lines') or {}
    approved_lines = [ln for ln, x in vl.items() if x['status'] == 'approved']
    S['voice'] = ('not_started' if not tk else 'approved' if vl and all(x['status'] == 'approved' for x in vl.values())
                  else 'waiting_review')
    art = st['art']
    S['art'] = ('not_started' if not art['concepts'] else 'approved' if art['by_scene'] and all(s in art['approved'] for s in art['by_scene'])
                else 'waiting_review')
    sbl = st['storyboards'][-1] if st['storyboards'] else None
    S['storyboard'] = ('approved' if sbl and sbl.get('decision') == 'approved' else 'waiting_review' if sbl else 'not_started')
    rend = [r for r in st['renders'] if r.get('state') == 'ok']
    S['draft'] = ('approved' if any(r.get('decision') == 'approved_as_draft' for r in rend) else 'waiting_review' if rend
                  else 'failed' if st['renders'] and st['renders'][-1].get('state') == 'failed' else 'not_started')
    fs = st['review']['findings']
    S['review'] = ('not_started' if not st['review']['runs'] else
                   'approved' if all(f['decision'] for f in fs.values()) and all(t['status'] == 'done' for t in st['fix_tasks'])
                   else 'waiting_review')
    g = st['gate']
    S['gate'] = 'approved' if g.get('authorized') else 'blocked' if g['plan'] and g['plan'].get('blockers') else 'waiting_review' if g['plan'] else 'not_started'
    for i, j in enumerate(st['jobs']):
        if any(k['kind'] == j['kind'] and k['state'] == 'finished' for k in st['jobs'][i + 1:]): continue
        if j['state'] == 'running': S[j['stage']] = 'processing'
        elif j['state'] in ('failed', 'interrupted') and S.get(j['stage']) in ('not_started', 'processing'): S[j['stage']] = j['state']
    stage = next((s for s in STAGES if S[s] != 'approved'), 'gate')
    steps = [{'id': s, 'name': STAGE_NAMES[s], 'state': S[s]} for s in STAGES]
    st['_counts'] = {'approved_lines': approved_lines}
    return stage, steps
