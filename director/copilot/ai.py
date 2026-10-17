"""The Co-Pilot's AI worker: one call per task, recorded with what it cost, never retried on its own.

Two workers share one interface (`call(studio, pid, kind, payload)`):

  MockWorker        fixtures and fixed rules; no model is called; every output says MOCK AI. Used for development,
                    tests and the browser journey. Free.
  ClaudeCodeWorker  the Claude Code CLI in headless mode (`claude -p`), with a lean prompt (own system prompt, no tools
                    unless the task needs them, structured JSON output) and a hard per-call spending cap
                    (--max-budget-usd). Verified in this workspace: it authenticates through the session's managed
                    provider (no API key); a default call reported $0.119, a lean call $0.009. Whether that is billed as
                    extra usage or counted against a subscription cannot be seen from inside, so it is treated as spending.

Spending rules (enforced here, in code):
  * a project's AI budget is $0 until the owner sets one (action cp_ai_budget, with a reason); at $0 the real worker
    refuses before starting the CLI;
  * the real worker is also off unless VD_AI_REAL_ENABLED=1 in the server's environment (a second lock);
  * each call is capped at what is left of the budget (and at PER_CALL_CAP); the reported cost is recorded whether
    the call succeeded or not;
  * one attempt per call: a failure is recorded and reported, never retried automatically;
  * every call (mock or real) is an event (cp_ai_call) and a line in VAR/copilot-ai-usage.jsonl (append-only).
Reviewers are separate calls with their own instructions: a reviewer sees the output and the research, never the
writer's reasoning, so a writer cannot approve its own work.
"""
from __future__ import annotations
import json, os, re, subprocess, time, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = Path(__file__).with_name('fixtures')
PER_CALL_CAP = 0.50
OVERSHOOT = 2.0             # what is left is divided by this to give the per-call cap (see call())
MIN_CALL_USD = 0.02
MOCK_LABEL = 'MOCK AI (fixtures; no model was called)'
CLAUDE_LABEL = 'Claude (headless Claude Code)'


class AIRefused(Exception):
    """The call was not made (no budget, disabled, unsupported). Nothing was spent."""


# ====================================================================== task kinds
ROLE = {'direction': 'researcher', 'research_check': 'research reviewer', 'script': 'writer', 'fact_check': 'fact checker',
        'quality_review': 'Arabic editor', 'revise_script': 'writer', 'pronunciation': 'voice editor', 'art_brief': 'art director',
        'style_eval': 'art director', 'asset_search': 'picture researcher', 'scene_review': 'art reviewer',
        'film_review': 'film reviewer', 'comment_to_change': 'editor'}
TOOLS = {'direction': 'WebSearch,WebFetch', 'asset_search': 'WebSearch,WebFetch', 'scene_review': 'Read', 'film_review': 'Read'}
_OBJ = {'type': 'object'}
SCHEMA = {
    'direction': {'type': 'object', 'required': ['topic', 'angle', 'duration_s', 'format', 'research'],
                  'properties': {'topic': {'type': 'string'}, 'angle': {'type': 'string'}, 'audience': {'type': 'string'},
                                 'duration_s': {'type': 'number'}, 'format': {'type': 'string'},
                                 'research': {'type': 'object', 'required': ['claims'], 'properties': {
                                     'claims': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'status', 'text', 'sources'],
                                                'properties': {'id': {'type': 'string'}, 'status': {'enum': ['verified', 'attributed', 'avoid', 'disputed']},
                                                               'text': {'type': 'string'}, 'sources': {'type': 'array', 'items': {'type': 'string'}},
                                                               'why': {'type': 'string'}, 'patterns': {'type': 'array', 'items': {'type': 'string'}}}}},
                                     'terms': {'type': 'array'}, 'verdict': {'type': 'string'}}}}},
    'script': {'type': 'object', 'required': ['lines', 'hooks'],
               'properties': {'lines': {'type': 'array', 'items': {'type': 'object', 'required': ['id', 'text', 'claims'],
                                                                  'properties': {'id': {'type': 'string'}, 'text': {'type': 'string'},
                                                                                 'claims': {'type': 'array', 'items': {'type': 'string'}}}}},
                              'hooks': {'type': 'object', 'required': ['options', 'recommended', 'reasons']}}},
    'fact_check': {'type': 'object', 'required': ['lines'], 'properties': {'lines': {'type': 'object'}}},
    'quality_review': {'type': 'object', 'required': ['lines'], 'properties': {'lines': {'type': 'object'}}},
    'revise_script': {'type': 'object', 'required': ['lines', 'claims', 'why'], 'properties': {'lines': {'type': 'object'}, 'claims': {'type': 'object'},
                                                                                              'why': {'type': 'string'}}},
    'pronunciation': {'type': 'object', 'required': ['entries'], 'properties': {'entries': {'type': 'array'}}},
    'art_brief': {'type': 'object', 'required': ['scenes'], 'properties': {'scenes': _OBJ, 'hook_visuals': _OBJ}},
    'style_eval': {'type': 'object', 'required': ['recommended', 'reasons'], 'properties': {'recommended': {'type': 'string'}, 'reasons': _OBJ}},
    'asset_search': {'type': 'object', 'required': ['needs'], 'properties': {'needs': {'type': 'array'}}},
    'scene_review': {'type': 'object', 'required': ['findings'], 'properties': {'findings': {'type': 'array'}}},
    'film_review': {'type': 'object', 'required': ['findings'], 'properties': {'findings': {'type': 'array'}}},
    'comment_to_change': {'type': 'object', 'properties': {'changes': _OBJ, 'needs_manual': {'type': 'boolean'}, 'why': {'type': 'string'}}},
}
SYSTEM = {
    'direction': 'You research a short Arabic documentary video (Reels/TikTok). Use only trustworthy sources (museum, archive, '
                 'patent office, peer-reviewed or established reference works, the brand itself only for its own claims). Every claim gets '
                 'its sources (URLs). Mark a popular but false or unprovable claim "avoid" with why and the Arabic patterns that state it. '
                 'Never present a claim as verified with fewer than one source. Say what still needs checking.',
    'research_check': 'You independently check a research file: unsupported claims, single-source claims, sources that are not '
                      'trustworthy, claims that contradict each other. You did not write it.',
    'script': 'You write a short Arabic (Modern Standard, clear Gulf-friendly) narration script, one sentence group per line, ids h '
              '(the hook), l2, l3 ... Every line lists the research claim ids it relies on. Never state an "avoid" claim except as an '
              'attributed belief. Also write 3-4 hooks (spoken, on_screen, visual, type, pays_off) and recommend one with reasons.',
    'fact_check': 'You are an independent fact checker. For every line: verdict supported | attributed | uncertain | unsupported | '
                  'contradicted, the claim ids that support or contradict it, and a short note. Do not rely on keyword matching: read '
                  'what the sentence asserts. When unsure say uncertain.',
    'quality_review': 'You are an independent Arabic editor: grammar, terminology, clarity for listening, speculation presented as '
                      'fact. Per line, a list of notes {code, severity: critical|major|minor|info, detail}.',
    'revise_script': 'Revise only the lines named in the findings or the owner note. Return {lines: {id: new text}, claims: {id: '
                     '[research claim ids that support the NEW sentence]}, why}. A rewritten sentence does not keep the old one\'s '
                     'claim ids: cite only what the new wording states, or none. Do not touch other lines.',
    'pronunciation': 'Propose draft-voice spellings (tashkeel or respelling) for names and foreign terms a machine voice may misread.',
    'art_brief': 'For each script line, the beat, a short on-screen banner (6 words or fewer), and parameters for the techniques '
                 'the engine can draw. Never invent a historical photograph.',
    'style_eval': 'Compare the style boards for this film and recommend one, with reasons per style.',
    'asset_search': 'List the real pictures this film needs per scene, with candidate sources and what licence evidence is needed. '
                    'Never claim a licence without a page that states it.',
    'scene_review': 'You are an independent art reviewer. Look at the scene stills and report problems a phone viewer would see. '
                    'Propose only safe parameter changes (zoom, text_size, slower, theme within the approved style).',
    'film_review': 'You are an independent film reviewer. Report creative problems with a time code and the scene.',
    'comment_to_change': 'Turn the owner comment into safe parameter changes, or say it needs a person.',
}


# ====================================================================== the call
def usage(studio, pid) -> dict:
    st = studio.state(pid)
    return st['copilot']['ai']


def call(studio, pid, kind, payload, actor='copilot') -> dict:
    """Run one AI task with the project's worker. Returns the output (a dict). Records the call either way."""
    if kind not in ROLE:
        raise AIRefused(f'unknown AI task {kind}')
    st = studio.state(pid)
    cp = st['copilot']
    worker = cp['settings'].get('worker', 'mock')
    cid = f'ai-{kind}-{uuid.uuid4().hex[:8]}'
    t0 = time.monotonic()
    if worker == 'mock':
        out = MockWorker().run(kind, payload)
        meta = {'worker': 'mock', 'label': MOCK_LABEL, 'cost_usd': 0.0, 'tokens': None, 'model': None}
    elif worker == 'claude-code':
        if os.environ.get('VD_AI_REAL_ENABLED') != '1':
            raise AIRefused('the real AI worker is off in this environment (VD_AI_REAL_ENABLED is not 1); use the mock worker')
        left = round(cp['ai']['budget_usd'] - cp['ai']['spent_usd'], 4)
        if left <= 0:
            raise AIRefused(f'AI usage budget for this project is ${cp["ai"]["budget_usd"]:.2f} with ${max(left, 0):.2f} left: '
                            'the owner must authorize a budget before a real AI call')
        # the CLI checks its budget between turns, so one call can go past --max-budget-usd by up to a turn. The cap is
        # therefore at most half of what is left: an overshoot as large as the cap itself still stays inside the budget.
        cap = round(min(left / OVERSHOOT, PER_CALL_CAP), 4)
        if cap < MIN_CALL_USD:
            raise AIRefused(f'only ${left:.2f} of the AI budget is left: too little for a safe call (it needs at least '
                            f'${MIN_CALL_USD * OVERSHOOT:.2f}); the owner must raise the budget')
        job = next((j for j in reversed(st['jobs']) if j.get('kind') == 'copilot' and j['state'] == 'running'), None)
        # reserve the whole cap before the CLI starts: a call cut short by a restart is still counted, in the event log
        # and in the append-only ledger
        rec0 = {'id': cid, 'kind': kind, 'role': ROLE[kind], 'worker': 'claude-code', 'label': CLAUDE_LABEL, 'key': job and (job.get('args') or {}).get('key'),
                'state': 'started', 'ok': None, 'cost_usd': None, 'reserved_usd': cap}
        studio.act(pid, 'cp_ai_call', rec0, actor='system')
        _ledger(studio, pid, rec0)
        try:
            out, meta = ClaudeCodeWorker(model=cp['settings'].get('model')).run(kind, payload, cap)
        except AIFailed as e:
            _record(studio, pid, cid, kind, {**e.meta, 'worker': 'claude-code', 'label': CLAUDE_LABEL, 'reserved_usd': cap}, None, str(e), t0, actor)
            raise
        meta['reserved_usd'] = cap
    else:
        raise AIRefused(f'unknown worker {worker}')
    _record(studio, pid, cid, kind, meta, out, None, t0, actor)
    return out


def _record(studio, pid, cid, kind, meta, out, error, t0, actor):
    cost = meta.get('cost_usd')
    rec = {'id': cid, 'kind': kind, 'role': ROLE[kind], 'worker': meta['worker'], 'label': meta['label'], 'ok': error is None, 'state': 'done',
           'cost_usd': None if cost is None else round(max(0.0, float(cost)), 6),     # unknown cost: the reserved cap is counted instead
           'reserved_usd': meta.get('reserved_usd'), 'over_cap': bool(cost and meta.get('reserved_usd') and cost > meta['reserved_usd']),
           'tokens': meta.get('tokens'), 'model': meta.get('model'),
           'duration_s': round(time.monotonic() - t0, 2), 'error': error,
           'output': studio.put(pid, json.dumps(out, ensure_ascii=False).encode(), 'json') if out is not None else None}
    studio.act(pid, 'cp_ai_call', rec, actor='system')
    _ledger(studio, pid, rec)


def _ledger(studio, pid, rec):
    with open(studio.var / 'copilot-ai-usage.jsonl', 'a', encoding='utf-8') as f:            # append-only, all projects
        f.write(json.dumps({'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'project': pid, **{k: v for k, v in rec.items() if k != 'output'}},
                           ensure_ascii=False) + '\n')


class AIFailed(Exception):
    def __init__(self, msg, meta):
        super().__init__(msg); self.meta = meta


# ====================================================================== real worker
class ClaudeCodeWorker:
    """`claude -p` with a lean prompt. One attempt; the cost it reports is returned even when it fails."""
    def __init__(self, model=None, binary='claude'):
        self.model, self.binary = model, binary

    def command(self, kind, payload, cap_usd) -> list[str]:
        prompt = f'Task: {kind}\nReply with JSON only, matching the schema.\n\nInput:\n' + json.dumps(payload, ensure_ascii=False)
        cmd = [self.binary, '-p', prompt, '--system-prompt', SYSTEM[kind], '--tools', TOOLS.get(kind, ''), '--disable-slash-commands',
               '--json-schema', json.dumps(SCHEMA[kind]), '--output-format', 'json', '--no-session-persistence',
               '--max-budget-usd', f'{cap_usd:.4f}', '--max-turns', '12' if kind in TOOLS else '3']
        if self.model:
            cmd += ['--model', self.model]
        return cmd

    def run(self, kind, payload, cap_usd):
        env = {k: v for k, v in os.environ.items() if k not in ('ELEVENLABS_API_KEY', 'FAL_KEY', 'HIGGSFIELD_API_KEY')}
        t0 = time.monotonic()
        try:
            r = subprocess.run(self.command(kind, payload, cap_usd), capture_output=True, text=True, timeout=900, env=env)
        except subprocess.TimeoutExpired:
            raise AIFailed('the AI call took longer than 15 minutes and was stopped', {'cost_usd': None, 'tokens': None, 'model': self.model})
        try:
            d = json.loads(r.stdout)
        except ValueError:
            raise AIFailed(f'no JSON from the CLI (exit {r.returncode}): {(r.stderr or r.stdout)[-300:]}', {'cost_usd': None, 'tokens': None, 'model': self.model})
        u = d.get('usage') or {}
        meta = {'worker': 'claude-code', 'label': CLAUDE_LABEL, 'cost_usd': d.get('total_cost_usd'),
                'tokens': {k: u.get(k) for k in ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')},
                'model': ','.join(sorted((d.get('modelUsage') or {}).keys())) or self.model, 'cli_seconds': round(time.monotonic() - t0, 2)}
        if d.get('is_error') or d.get('subtype') != 'success' or not isinstance(d.get('structured_output'), dict):
            raise AIFailed(f"AI call failed: {str(d.get('result') or d.get('subtype'))[:300]}", meta)
        return d['structured_output'], meta


# ====================================================================== mock worker
def _fixture_for(text: str):
    for f in sorted(FIX.glob('*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        if any(m.lower() in (text or '').lower() for m in d.get('match', [])):
            return d
    return None


MOCK_INJECT: dict = {}        # test hook (server test mode only): {'scene_review': {scene: [finding, ...]}} added to the mock reviewer's answer


class MockWorker:
    """Deterministic stand-in for the AI roles. It never pretends: every output carries `mock: true` and the label."""

    def run(self, kind, payload) -> dict:
        out = getattr(self, 'k_' + kind)(payload)
        out['mock'] = True; out['label'] = MOCK_LABEL
        return out

    # ---------------------------------------------------------------- research and direction
    def k_direction(self, p):
        fx = _fixture_for(' '.join(str(p.get(k, '')) for k in ('idea', 'title')))
        if fx is None:
            return {'unsupported': True, 'reason': 'The mock AI only has prepared research for the Rolex Oyster idea. '
                    'A real research run needs the real AI worker and an AI budget authorized by the owner.'}
        d = dict(fx['direction'])
        research = json.loads((ROOT / d.pop('research')).read_text(encoding='utf-8'))
        note = p.get('note') or ''
        m = re.search(r'(\d{2,3})\s*(?:s|sec|ث|ثانية)', note)
        if m: d['duration_s'] = int(m.group(1))
        if p.get('duration_s') and not m: d['duration_s'] = p['duration_s']
        verify = []
        for c in research['claims']:
            if c['status'] == 'attributed': verify.append({'claim': c['id'], 'why': 'attributed: say who claims it', 'why_ar': 'منسوب: اذكر من يقوله'})
            elif c['status'] == 'verified' and len(c.get('sources', [])) < 2: verify.append({'claim': c['id'], 'why': 'one source only', 'why_ar': 'مصدر واحد فقط'})
            elif c.get('careful'): verify.append({'claim': c['id'], 'why': c['careful'], 'why_ar': 'تفصيل يجب الحذر فيه'})
        return {**d, 'research': research, 'claims_to_verify': verify,
                'note_answer': ('MOCK AI: duration taken from your note; the mock does not rewrite the angle' if note else '')}

    def k_research_check(self, p):
        F = []
        for c in p['research']['claims']:
            if c['status'] in ('verified', 'attributed') and not c.get('sources'):
                F.append({'claim': c['id'], 'code': 'NO_SOURCE', 'severity': 'critical', 'detail': 'no source'})
            elif c['status'] == 'verified' and len(c['sources']) == 1:
                F.append({'claim': c['id'], 'code': 'SINGLE_SOURCE', 'severity': 'minor', 'detail': 'one source only: keep the wording close to it'})
        return {'findings': F}

    # ---------------------------------------------------------------- script
    def _script_fixture(self):
        return json.loads((ROOT / 'uat/rolex/script.json').read_text(encoding='utf-8'))

    def k_script(self, p):
        fx = _fixture_for(p.get('idea', '') + ' ' + p.get('title', ''))
        if fx is None:
            return {'unsupported': True, 'reason': 'no prepared script for this idea in the mock AI'}
        s = self._script_fixture()
        hooks = json.loads((ROOT / 'uat/rolex/hooks.json').read_text(encoding='utf-8'))
        lines = [{'id': l['id'], 'text': l['text'], 'claims': fx['claim_map'].get(l['id'], [])} for l in s['v1'] if l.get('role') != 'hook']
        opts = [{k: o[k] for k in ('id', 'type', 'spoken', 'on_screen', 'visual', 'pays_off')} for o in hooks['options']]
        for o in opts:
            o['pays_off_line'] = re.findall(r'l\d+', o['pays_off'])[0]
        return {'lines': lines, 'hooks': {'options': opts, 'recommended': hooks['recommended'], 'reasons': hooks['reasons']}}

    def k_fact_check(self, p):
        # a stand-in for a reader: what each clause asserts (not the project's keyword rule, so the two signals stay independent)
        from .factcheck import assertions, subject_hits
        res = p['research']
        status = {c['id']: c['status'] for c in res['claims']}
        out = {}
        for ln in p['lines']:
            ids = [c for c in (ln.get('claims') or []) if c in status]
            ass = [x for x in assertions(ln['text']) if not x['attributed'] and not x['negated']]
            hits = sorted({h for x in ass if x['kind'] != 'first_time' for h in subject_hits(x['clause'], res)})
            if hits:
                v, note = 'contradicted', f'states {", ".join(hits)}, which the research marks avoid'
            elif ass and not any(status[c] in ('verified', 'attributed') for c in ids):
                v, note = 'uncertain', f'asserts «{ass[0]["phrase"]}» without a supporting claim'
            elif ids and all(status[c] == 'avoid' for c in ids):
                v, note = 'attributed', 'reports the belief as a belief'
            elif any(status[c] == 'attributed' for c in ids):
                v, note = 'attributed', 'relies on an attributed claim: keep the attribution'
            elif ids:
                v, note = 'supported', ''
            else:
                v, note = 'uncertain', 'no research claim behind this line'
            out[ln['id']] = {'verdict': v, 'claims': ids, 'note': note}
        return {'lines': out}

    def k_quality_review(self, p):
        fx = _fixture_for('rolex') or {}
        v1 = {l['id']: l['text'] for l in self._script_fixture()['v1']}
        out = {}
        for ln in p['lines']:
            q = fx.get('quality', {}).get(ln['id'])
            if q and (q['severity'] == 'info' or ln['text'] == v1.get(ln['id'])):      # a major note only while the v1 wording is there
                out[ln['id']] = [q]
        return {'lines': out}

    def k_revise_script(self, p):
        fx = _fixture_for('rolex') or {}
        cur = {l['id']: l['text'] for l in p['lines']}
        if p.get('owner'):
            n = p.get('owner_round', 0)
            revs = fx.get('owner_revisions', [])
            if n >= len(revs):
                return {'lines': {}, 'why': 'MOCK AI: no further prepared revision. Edit the sentence yourself, or use the real AI worker.'}
            got = {k: v for k, v in revs[n]['lines'].items() if k in cur}
            return {'lines': got, 'claims': {k: fx['claim_map'].get(k, []) for k in got}, 'why': revs[n]['why']}
        ch = self._script_fixture()['v2_changes']
        targets = set(p.get('targets') or [])
        got = {k: v for k, v in ch.items() if k in cur and k in targets and cur[k] != v}
        # the prepared revisions restate the same researched facts, so the fixture cites the same claims for them
        return {'lines': got, 'claims': {k: fx['claim_map'].get(k, []) for k in got},
                'why': 'MOCK AI: answered the fact check and the editor (prepared revision)'}

    # ---------------------------------------------------------------- voice, art, assets
    def k_pronunciation(self, p):
        fx = _fixture_for('rolex') or {}
        text = ' '.join(l['text'] for l in p['lines'])
        from ..studio import checks
        ws = set(checks.words(text))
        out = []
        for e in fx.get('pronunciation', []):
            if e['word'] in ws:
                out.append({**e, 'lines': [l['id'] for l in p['lines'] if e['word'] in checks.words(l['text'])]})
        return {'entries': out}

    def k_art_brief(self, p):
        b = json.loads((ROOT / 'uat/rolex/art_brief.json').read_text(encoding='utf-8'))
        b.pop('_note', None)
        for ln in p['lines']:                              # a line the fixture brief does not know gets a type card
            if ln['id'] not in b['scenes']:
                b['scenes'][ln['id']] = {'beat': 'text', 'banner': None, 'default': 'kinetic_type', 'dur': 5.0, 'theme': 'tk-bone',
                                         'concepts': {'kinetic_type': {'lines': [{'text': ' '.join(ln['text'].split()[:3]), 'size': 84}], 'y': 520}}}
        return b

    def k_style_eval(self, p):
        ids = [d['id'] for d in p['directions'] if d.get('ready')]
        rec = 'paper-story' if 'paper-story' in ids else ids[0]
        why = {'paper-story': 'Warm and consistent; draws people, places and the swim without inventing photographs; the brand already uses paper.',
               'technical': 'Best for the crown mechanism (l3–l7) and labelled as a simplified principle; colder for the swim and the advert.',
               'ink-keynote': 'Strong contrast and premium feel; dark scenes are harder to read on a phone in daylight.'}
        why_ar = {'paper-story': 'دافئ ومتّسق، يرسم الأشخاص والأماكن والسباحة دون اختراع صور، والعلامة تستخدم الورق أصلًا',
                  'technical': 'الأفضل لآلية التاج ومعلَّم كرسم توضيحي، لكنه بارد في مشاهد السباحة والإعلان',
                  'ink-keynote': 'تباين قوي وإحساس فاخر، لكن المشاهد الداكنة أصعب قراءة على الهاتف في النهار'}
        return {'recommended': rec, 'ranking': [rec] + [i for i in ids if i != rec], 'reasons': {i: why.get(i, 'ready') for i in ids},
                'reasons_ar': {i: why_ar.get(i, '') for i in ids}}

    def k_asset_search(self, p):
        fx = _fixture_for('rolex') or {}
        return {'needs': [dict(a, candidates=[], found='no licensed file found by the mock (offline); add your own or a licensed one')
                          for a in fx.get('assets', []) if a['scene'] in p.get('scenes', [])]}

    def k_scene_review(self, p):
        fx = _fixture_for('rolex') or {}
        applied = set(p.get('changes_applied') or [])
        F = []
        for n in fx.get('scene_review', {}).get(p['scene'], []):
            if not all(f'{k}:{v}' in applied for k, v in (n.get('fix') or {}).items()):
                F.append(dict(n))
        F += [dict(x) for x in MOCK_INJECT.get('scene_review', {}).get(p['scene'], [])]
        if p.get('technique') == 'neutral_placeholder':
            F.append({'code': 'PLACEHOLDER_PERSON', 'severity': 'major', 'detail': 'a placeholder silhouette stands in for a real person',
                      'detail_ar': 'ظلّ بديل مكان شخص حقيقي', 'fix': None})
        return {'findings': F}

    def k_film_review(self, p):
        fx = _fixture_for('rolex') or {}
        at = {s['id']: s for s in p['scenes']}
        return {'findings': [dict(f, t=round(at[f['scene']]['start'] + 1.0, 2)) for f in fx.get('film_review', []) if f['scene'] in at]}

    def k_comment_to_change(self, p):
        t = (p.get('text') or '').lower()
        ch = {}
        if re.search(r'أكبر|كبّر|كبر|bigger|larger|small text|صغير', t): ch['text_size'] = '1.2'
        if re.search(r'أغمق|داكن|darker', t): ch['theme'] = 'tk-ink'
        if re.search(r'أفتح|lighter', t): ch['theme'] = 'tk-bone'
        if re.search(r'أبطأ|ببطء|slower', t): ch['slower'] = '1.4'
        if re.search(r'أقرب|قرّب|closer|zoom', t): ch['zoom'] = '1.18'
        if ch:
            return {'changes': ch, 'why': 'MOCK AI: matched words in the comment to safe changes'}
        return {'changes': {}, 'needs_manual': True, 'why': 'MOCK AI could not turn this comment into a safe change: it needs a person'}
