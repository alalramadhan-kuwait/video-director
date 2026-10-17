"""Co-Pilot rules: mode, approval engine (content hashes, targeted invalidation), the AI worker's spending locks,
the fact check (Rolex regressions), owner-only gates, exceptions, voice processing, picture licences, paid locks.
Fast tests: no rendering. The draft voice is offline-mock; the network is blocked; the AI is the mock worker or a
fake `claude` binary written into a temporary folder."""
from tests import _guard  # noqa: F401
import json, os, stat, sys, tempfile, unittest
from pathlib import Path

os.environ['VD_DRAFT_VOICE'] = 'offline-mock'
os.environ['VD_COPILOT_MANUAL_STEP'] = '1'
from director.studio.store import Studio, Refused
from director.studio import jobs
from director.copilot import ai, approvals as A, factcheck as FC, orchestrator as O, styles, scenes as SC, api as CA
from director.voice.gateway import PaidGateway, ElevenLabsProvider, PaidCallRefused
from director.voice.takes import TakeStore
from director.ledger import Ledger
from tests.test_voice import MockTransport

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = json.loads((ROOT / 'research/rolex-oyster.json').read_text(encoding='utf-8'))
IDEA = 'How the Rolex Oyster (1926) made a waterproof watch people trusted'


def run_step(S, pid, key_prefix=None, first=True):
    p = O.plan(S, pid)
    s = p['step'] if first else next((x for x in p['steps'] if x.key.startswith(key_prefix)), None)
    assert s is not None, p
    if key_prefix: assert s.key.startswith(key_prefix), (s.key, key_prefix)
    jobs.start(S, pid, 'copilot', s.stage, s.what, s.units, s.fn, {'key': s.key, **s.args}, sync=True)
    j = S.state(pid)['jobs'][-1]
    assert j['state'] == 'finished', j
    return s.key


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.var = Path(self.tmp.name)
        self.S = CA.studio(self.var)
        code, r = CA.handle(self.var, {'action': 'create', 'args': {'title': 'Rolex Oyster', 'idea': IDEA, 'brand': 'timekeeper', 'mode': 'copilot'}})
        assert code == 200, r
        self.pid = r['project']

    def tearDown(self):
        for p in self.var.rglob('*'):
            if p.is_file(): os.chmod(p, 0o644)
        self.tmp.cleanup()

    def owner(self, action, args):
        code, r = CA.handle(self.var, {'project': self.pid, 'action': action, 'args': args})
        if code != 200: raise Refused(r['reason'])
        return r

    def gate(self, g, decision='approved', **kw):
        st = self.S.state(self.pid)
        if 'playback' in kw and 'of' not in kw['playback']:            # what the page sends: the media that was played
            kw['playback'] = {**kw['playback'], 'of': st['copilot']['voice_mix']['file'] if g == 'G3' else A.current(st)['G5']['ref']}
        return self.owner('cp_gate', {'gate': g, 'decision': decision, 'content_hash': A.current(st)[g]['hash'], **kw})

    def to_g2(self):
        run_step(self.S, self.pid, 'direction:1'); run_step(self.S, self.pid, 'direction_check')
        self.gate('G1')
        run_step(self.S, self.pid, 'script:'); run_step(self.S, self.pid, 'script_check:1')
        run_step(self.S, self.pid, 'script_revise:1:auto'); run_step(self.S, self.pid, 'script_check:2')
        self.assertIn('G2', O.plan(self.S, self.pid)['waiting'])

    def to_g3(self):
        self.to_g2()
        self.gate('G2')
        run_step(self.S, self.pid, 'pron:'); run_step(self.S, self.pid, 'voice:'); run_step(self.S, self.pid, 'mix:')


class TestMode(Env):
    def test_copilot_is_recorded_and_auto_is_not_available(self):
        st = self.S.state(self.pid)
        self.assertEqual(st['copilot']['mode'], 'copilot')
        code, r = CA.handle(self.var, {'action': 'create', 'args': {'title': 'X', 'idea': 'y', 'brand': 'timekeeper', 'mode': 'auto'}})
        self.assertEqual(code, 422); self.assertIn('not yet implemented', r['reason'])

    def test_existing_classic_projects_are_never_changed(self):
        pid = self.S.act(None, 'create_project', {'title': 'Old', 'idea': 'old one', 'brand': 'timekeeper'})['project']
        st = self.S.state(pid)
        self.assertIsNone(st['copilot']['mode'])
        self.assertEqual(O.plan(self.S, pid)['step'], None)
        self.assertEqual(next(p for p in CA.projects(self.var) if p['id'] == pid)['mode'], 'classic')

    def test_switch_to_manual_keeps_approvals_and_stops_the_copilot(self):
        run_step(self.S, self.pid, 'direction:1'); run_step(self.S, self.pid, 'direction_check')
        self.gate('G1')
        self.owner('cp_mode', {'mode': 'manual'})
        st = self.S.state(self.pid)
        self.assertEqual(st['copilot']['mode'], 'manual')
        self.assertTrue(A.validity(st)['G1']['valid'])                 # the approval is still there
        self.assertIsNone(O.plan(self.S, self.pid)['step'])            # nothing runs on its own
        with self.assertRaises(Refused): self.owner('cp_control', {'op': 'resume'})
        self.owner('cp_mode', {'mode': 'copilot'})
        self.assertEqual(self.S.state(self.pid)['copilot']['run'], 'stopped')   # switching back does not start work by itself


class TestApprovals(Env):
    def test_gate_needs_the_exact_content_the_owner_saw(self):
        run_step(self.S, self.pid, 'direction:1'); run_step(self.S, self.pid, 'direction_check')
        with self.assertRaises(Refused):
            self.owner('cp_gate', {'gate': 'G1', 'decision': 'approved', 'content_hash': 'stale'})
        self.gate('G1')
        with self.assertRaises(Refused): self.gate('G1')                # already approved for this version

    def test_settings_change_outdates_the_direction_and_everything_built_on_it(self):
        self.to_g2(); self.gate('G2')
        st = self.S.state(self.pid)
        self.assertTrue(A.validity(st)['G2']['valid'])
        self.owner('cp_settings', {'duration_s': 60})
        val = A.validity(self.S.state(self.pid))
        self.assertFalse(val['G1']['valid']); self.assertIn('direction changed', val['G1']['why'])
        self.assertFalse(val['G2']['valid']); self.assertIn('G1', val['G2']['why'])
        self.assertIsNotNone(val['G2']['approved'])                     # the earlier approval is kept, marked outdated

    def test_only_the_approved_script_version_is_used_downstream(self):
        self.to_g2()
        v = self.S.state(self.pid)['scripts'][-1]['v']
        self.gate('G2')
        from director.studio.voice import approved_script
        self.assertEqual(approved_script(self.S.state(self.pid))['v'], v)

    def test_voice_approval_is_per_line_and_a_changed_line_needs_listening_again(self):
        self.to_g3()
        st = self.S.state(self.pid)
        mix = st['copilot']['voice_mix']
        with self.assertRaises(Refused):                                # nothing heard
            self.gate('G3', playback={'covered': []})
        self.gate('G3', playback={'covered': [[0, mix['seconds']]]})
        st = self.S.state(self.pid)
        self.assertTrue(A.validity(st)['G3']['valid'])
        self.assertTrue(all(x['status'] == 'approved' for x in st['voice']['lines'].values()))
        # a speed change on one line makes a new take: only that line goes back to the owner; the approved take stays in use
        approved_l5 = st['voice']['lines']['l5']['take']
        old_mix = st['copilot']['voice_mix']['file']
        self.owner('cp_voice_adjust', {'line': 'l5', 'speed': 0.9})
        run_step(self.S, self.pid, 'adjust:'); run_step(self.S, self.pid, 'mix:')
        st = self.S.state(self.pid)
        self.assertEqual(st['voice']['lines']['l5']['take'], approved_l5)
        self.assertEqual(A.current(st)['G3']['pending'], ['l5'])
        self.assertIn('G3', O.plan(self.S, self.pid)['waiting'])
        mix = st['copilot']['voice_mix']
        seg = next(x for x in mix['segments'] if x['line'] == 'l5')
        with self.assertRaises(Refused): self.gate('G3', playback={'covered': [[0, seg['start']]]})     # l5 not heard
        with self.assertRaises(Refused):                                                                    # re-audit N4: heard an older play-all
            self.gate('G3', playback={'covered': [[0, mix['seconds']]], 'of': old_mix})
        self.gate('G3', playback={'covered': [[seg['start'], seg['end']]]})                                 # only l5 needs listening
        st = self.S.state(self.pid)
        self.assertNotEqual(st['voice']['lines']['l5']['take'], approved_l5)
        self.assertTrue(A.validity(st)['G3']['valid'])


    def test_withdrawing_a_correction_returns_to_the_approved_take_without_looping(self):
        """Re-audit N1: correct a word, withdraw the correction (and B → C → B): the plan settles, Gate 3 stays decidable."""
        self.to_g3()
        mix = self.S.state(self.pid)['copilot']['voice_mix']
        self.gate('G3', playback={'covered': [[0, mix['seconds']]]})
        st = self.S.state(self.pid)
        approved = {l: x['take'] for l, x in st['voice']['lines'].items()}
        line = next(l for l, x in st['voice']['lines'].items() if 'أويستر' in x['text'])
        self.owner('cp_pron', {'word': 'أويستر', 'respell': 'أُويْسْتَر', 'lines': [line]})
        run_step(self.S, self.pid, 'respell:'); run_step(self.S, self.pid, 'mix:')
        st = self.S.state(self.pid)
        self.assertEqual(A.current(st)['G3']['pending'], [line])
        pr = st['copilot']['pron'][-1]['id']
        self.owner('cp_pron', {'op': 'decide', 'id': pr, 'decision': 'rejected'})          # withdraw it
        st = self.S.state(self.pid)
        self.assertEqual(O.voicekit.effective_takes(st), approved)                         # the approved takes again
        p = O.plan(self.S, self.pid)
        self.assertFalse([s.key for s in p['steps'] if s.key.startswith('respell:')], p)
        self.assertTrue(A.validity(st)['G3']['valid'])                                    # nothing new to decide
        for _ in range(5):                                                                # whatever is offered finishes
            p = O.plan(self.S, self.pid)
            if not p['step'] or p['step'].stage != 'voice': break
            run_step(self.S, self.pid)
        self.assertFalse(any(s.key.startswith(('respell:', 'mix:')) for s in O.plan(self.S, self.pid)['steps']))
        # B → C → B: the dictionary returns to a spelling that already has a take
        self.owner('cp_pron', {'word': 'أويستر', 'respell': 'أُويْسْتَر', 'lines': [line]})
        st = self.S.state(self.pid)
        b = O.voicekit.effective_takes(st)[line]
        self.assertNotEqual(b, approved[line])                                             # B's take exists already: no respell
        self.assertFalse([s.key for s in O.plan(self.S, self.pid)['steps'] if s.key.startswith('respell:')])
        self.owner('cp_pron', {'word': 'أويستر', 'respell': 'أوِيسْتَر', 'lines': [line]})
        run_step(self.S, self.pid, 'respell:', first=False)
        self.owner('cp_pron', {'word': 'أويستر', 'respell': 'أُويْسْتَر', 'lines': [line]})
        st = self.S.state(self.pid)
        self.assertEqual(O.voicekit.effective_takes(st)[line], b)
        self.assertFalse([s.key for s in O.plan(self.S, self.pid)['steps'] if s.key.startswith('respell:')])
        run_step(self.S, self.pid, 'mix:')
        st = self.S.state(self.pid)
        seg = next(x for x in st['copilot']['voice_mix']['segments'] if x['line'] == line)
        self.gate('G3', playback={'covered': [[seg['start'], seg['end']]]})
        self.assertTrue(A.validity(self.S.state(self.pid))['G3']['valid'])

class TestScriptGate(Env):
    def test_critical_line_needs_an_evidence_override_and_majors_need_acknowledging(self):
        self.to_g2()
        self.owner('cp_line_edit', {'line': 'l13', 'text': 'اخترعت رولكس الساعة المقاومة للماء عام ستةٍ وعشرين.'})
        run_step(self.S, self.pid, 'script_check:3')
        st = self.S.state(self.pid)
        mc = O.merged_check(st['copilot'], 3)
        self.assertEqual(mc['lines']['l13']['severity'], 'critical')    # the plainest paraphrase the keyword rule missed
        with self.assertRaises(Refused): self.gate('G2')
        with self.assertRaises(Refused): self.gate('G2', overrides={'l13': 'the check is wrong here'})   # a sentence is not evidence
        with self.assertRaises(Refused):                                # re-audit D4: c4 is not linked to this edited line
            self.gate('G2', overrides={'l13': 'c4 contradicts it — kept on purpose for the test'})
        with self.assertRaises(Refused): self.gate('G2', overrides={'l13': 'https://a.bc nothing to see here really'})
        self.gate('G2', overrides={'l13': 'https://www.example-archive.org/oyster-1926 the 1926 advert says so; kept on purpose for the test'})
        st = self.S.state(self.pid)
        self.assertEqual(st['scripts'][-1]['status'], 'approved')

    def test_hook_change_makes_a_new_version_and_the_old_approval_is_outdated(self):
        self.to_g2(); self.gate('G2')
        with self.assertRaises(Refused): self.owner('cp_hook', {'hook': 'H1'})       # already the opening line
        self.owner('cp_hook', {'hook': 'H3'})
        st = self.S.state(self.pid)
        lines = self.S._version_lines(self.pid, st['scripts'][-1])['lines']
        h3 = next(o for o in st['hooks']['options'] if o['id'] == 'H3')
        self.assertEqual(lines[0]['text'], h3['spoken'])
        self.assertFalse(A.validity(st)['G2']['valid'])
        with self.assertRaises(Refused): self.gate('G2')                # its fact check has not run yet

    def test_rejected_script_is_revised_by_the_ai_and_waits_again(self):
        self.to_g2()
        self.gate('G2', decision='rejected', note='l2 is too long')
        k = run_step(self.S, self.pid, 'script_revise:2:owner')
        st = self.S.state(self.pid)
        self.assertEqual(st['scripts'][-1]['v'], 3)
        self.assertIn('MOCK AI', st['copilot']['script_meta']['3']['why'])
        run_step(self.S, self.pid, 'script_check:3')
        self.assertIn('G2', O.plan(self.S, self.pid)['waiting'])


class TestFactCheck(unittest.TestCase):
    MISSED = ['اخترعت رولكس الساعة المقاومة للماء عام ستةٍ وعشرين.', 'رولكس هي مخترعة ساعة اليد المقاومة للماء.',
              'لم يعرف العالم ساعةً مقاومةً للماء قبل أويستر.', 'كانت رولكس رائدةَ الساعات المقاومة للماء، فهي أول من صنعها.',
              'مع أويستر بدأ عصر الساعات المقاومة للماء؛ لم تكن قبلها ساعة كهذه.', 'أوّل ساعة بالعالم ما يدخلها مَي.',
              'قبل أويستر، لم تكن هناك ساعة يد تصمد في الماء.']

    def check(self, text, claims=()):
        from director.studio import checks
        lines = [{'id': 'x', 'text': text, 'claims': list(claims)}]
        out = ai.MockWorker().run('fact_check', {'lines': lines, 'research': RESEARCH})
        return FC.merge(lines, RESEARCH, checks.check_version(lines, RESEARCH, []), out)['x']

    def test_missed_paraphrases_are_critical(self):
        for p in self.MISSED:
            self.assertEqual(self.check(p)['severity'], 'critical', p)

    def test_former_false_positive_is_not_a_block_but_is_shown(self):
        r = self.check('في أول مرة نزلت فيها الساعة إلى الماء، بقيت تعمل.')
        self.assertNotEqual(r['severity'], 'critical'); self.assertEqual(r['verdict'], 'disputed')

    def test_attributed_and_negated_and_questions_are_not_claims(self):
        self.assertNotEqual(self.check('يقولون إن رولكس صنعت أول ساعة يدٍ مقاومةٍ للماء… والحقيقة أذكى من ذلك.', ['c4'])['severity'], 'critical')
        self.assertNotEqual(self.check('رولكس لم تخترع الساعة المقاومة للماء… لكنها جعلت العالم يثق بها.', ['c4'])['severity'], 'critical')
        self.assertEqual(FC.assertions('أول ساعة مقاومة للماء؟ ليس تمامًا'), [])

    def test_true_line_with_sources_passes_and_unsourced_line_is_uncertain(self):
        self.assertEqual(self.check('مرسيدس غلايتسه، أول بريطانيةٍ تعبر بحر المانش سباحةً.', ['c7'])['severity'], 'none')
        self.assertEqual(self.check('كانت الساعة جميلة جدًا.')['verdict'], 'uncertain')

    def test_override_must_cite_evidence(self):
        self.assertFalse(FC.override_ok('the check is wrong here', RESEARCH))
        self.assertFalse(FC.override_ok('ok ok ok ok ok ok', RESEARCH))
        self.assertTrue(FC.override_ok('c8 says she wore it on the second swim', RESEARCH))
        self.assertTrue(FC.override_ok('the archive page shows the swim: https://example.org/source', RESEARCH))
        self.assertFalse(FC.override_ok('c1', RESEARCH))                       # a bare token is not an explanation (audit D4)
        self.assertFalse(FC.override_ok('see c1 ok', RESEARCH))
        self.assertFalse(FC.override_ok('https://example.org/x', RESEARCH))

    def test_unsourced_priority_claims_are_critical_and_set_phrases_are_not(self):
        self.assertEqual(self.check('كانت أويستر أول ساعة يد يمكن الغوص بها في المحيط.')['severity'], 'critical')
        self.assertEqual(self.check('Rolex invented the waterproof watch.')['severity'], 'critical')
        self.assertNotEqual(self.check('نشرت رولكس القصة على الصفحة الأولى لصحيفة ديلي ميل.', ['c9'])['severity'], 'critical')

    def test_a_question_on_screen_is_not_a_claim(self):
        from director.studio import checks
        c = next(x for x in RESEARCH['claims'] if x['status'] == 'avoid')
        self.assertEqual(checks._claim_hits('أول ساعة مقاومة للماء؟ ليس تمامًا', c), [])
        self.assertTrue(checks._claim_hits('صنعت رولكس أول ساعة مقاومة للماء.', c))


class TestAIWorker(Env):
    def fake_claude(self, body: dict, exit_code=0):
        d = self.var / 'bin'; d.mkdir(exist_ok=True)
        log = self.var / 'claude-calls.log'
        f = d / 'claude'
        f.write_text('#!/bin/sh\necho CALL >> ' + str(log) + '\necho "$@" >> ' + str(log) + '\ncat <<\'EOF\'\n' + json.dumps(body) + '\nEOF\nexit ' + str(exit_code) + '\n')
        f.chmod(0o755)
        return d, log

    def test_mock_outputs_are_labelled(self):
        out = ai.call(self.S, self.pid, 'direction', {'idea': IDEA, 'title': 't'})
        self.assertTrue(out['mock']); self.assertIn('MOCK', out['label'])
        c = self.S.state(self.pid)['copilot']['ai']['calls'][-1]
        self.assertEqual((c['worker'], c['cost_usd']), ('mock', 0.0))
        self.assertTrue((self.var / 'copilot-ai-usage.jsonl').read_text().strip())

    def test_real_worker_is_locked_without_env_and_without_budget(self):
        self.owner('cp_settings', {'worker': 'claude-code'})
        os.environ.pop('VD_AI_REAL_ENABLED', None)
        with self.assertRaises(ai.AIRefused): ai.call(self.S, self.pid, 'fact_check', {'lines': [], 'research': RESEARCH})
        os.environ['VD_AI_REAL_ENABLED'] = '1'
        try:
            with self.assertRaises(ai.AIRefused) as e: ai.call(self.S, self.pid, 'fact_check', {'lines': [], 'research': RESEARCH})
            self.assertIn('$0.00', str(e.exception))
            self.assertEqual(self.S.state(self.pid)['copilot']['ai']['calls'], [])     # refused before anything ran
        finally:
            os.environ.pop('VD_AI_REAL_ENABLED', None)

    def test_budget_needs_a_reason_and_calls_are_capped_recorded_and_never_retried(self):
        with self.assertRaises(Refused): self.owner('cp_ai_budget', {'usd': 1})
        self.owner('cp_ai_budget', {'usd': 0.10, 'note': 'owner test of the real worker'})
        self.owner('cp_settings', {'worker': 'claude-code'})
        d, log = self.fake_claude({'type': 'result', 'subtype': 'success', 'is_error': False, 'total_cost_usd': 0.03,
                                   'usage': {'input_tokens': 5, 'output_tokens': 7}, 'modelUsage': {'claude-test': {}},
                                   'structured_output': {'lines': {}}})
        os.environ['VD_AI_REAL_ENABLED'] = '1'; old = os.environ['PATH']; os.environ['PATH'] = f'{d}:{old}'
        try:
            ai.call(self.S, self.pid, 'fact_check', {'lines': [], 'research': RESEARCH})
            args = log.read_text()
            for flag in ('--tools', '--json-schema', '--no-session-persistence', '--output-format json', '--disable-slash-commands', '--max-budget-usd 0.0500'):
                self.assertIn(flag, args)
            self.assertEqual(self.S.state(self.pid)['copilot']['ai']['spent_usd'], 0.03)
            led = [json.loads(x) for x in (self.var / 'copilot-ai-usage.jsonl').read_text().splitlines()]
            self.assertEqual([x['state'] for x in led[-2:]], ['started', 'done'])           # the ledger knows a call began
            # the cap is half of what is left (the CLI can overshoot by a turn): 0.07 left → 0.035, then 0.04 → 0.02
            ai.call(self.S, self.pid, 'fact_check', {'lines': [], 'research': RESEARCH})
            self.assertIn('--max-budget-usd 0.0350', log.read_text().split('CALL')[-1])
            ai.call(self.S, self.pid, 'fact_check', {'lines': [], 'research': RESEARCH})
            self.assertIn('--max-budget-usd 0.0200', log.read_text().split('CALL')[-1])
            with self.assertRaises(ai.AIRefused): ai.call(self.S, self.pid, 'fact_check', {'lines': [], 'research': RESEARCH})
            self.assertLessEqual(self.S.state(self.pid)['copilot']['ai']['spent_usd'], 0.10)
            # a failed call: its reported cost is recorded and it is not retried
            self.owner('cp_ai_budget', {'usd': 1.0, 'note': 'owner raises the budget for the test'})
            d, log = self.fake_claude({'type': 'result', 'subtype': 'error_max_budget_usd', 'is_error': True, 'total_cost_usd': 0.01, 'usage': {}}, 1)
            n0 = log.read_text().count('CALL')
            with self.assertRaises(ai.AIFailed): ai.call(self.S, self.pid, 'fact_check', {'lines': [], 'research': RESEARCH})
            self.assertEqual(log.read_text().count('CALL') - n0, 1)                     # one attempt, no retry
            c = self.S.state(self.pid)['copilot']['ai']['calls'][-1]
            self.assertEqual((c['ok'], c['cost_usd']), (False, 0.01))
        finally:
            os.environ['PATH'] = old; os.environ.pop('VD_AI_REAL_ENABLED', None)


    def test_a_real_ai_call_cut_off_by_a_restart_is_not_run_again_by_itself(self):     # audit D10
        self.S.act(self.pid, 'cp_ai_call', {'id': 'ai-x', 'kind': 'direction', 'role': 'r', 'worker': 'claude-code', 'label': 'x', 'key': 'direction:1',
                                            'state': 'started', 'ok': None, 'cost_usd': None, 'reserved_usd': 0.25}, actor='system')
        st = self.S.state(self.pid)
        self.assertIn('direction:1', O.failed_keys(st))
        self.assertEqual(st['copilot']['ai']['spent_usd'], 0.25)                           # the reserved cap is counted
        self.assertNotEqual((O.plan(self.S, self.pid)['step'] or O.Step('', '', '', None, {})).key, 'direction:1')
        self.owner('cp_control', {'op': 'retry', 'key': 'direction:1'})
        self.assertNotIn('direction:1', O.failed_keys(self.S.state(self.pid)))


class TestOwnerOnly(Env):
    def test_the_page_cannot_act_as_the_copilot(self):
        for a in ('cp_scene', 'cp_film', 'cp_ai_call', 'cp_check', 'cp_ready', 'cp_exception', 'voice_take', 'render', 'review'):
            code, r = CA.handle(self.var, {'project': self.pid, 'action': a, 'args': {}})
            self.assertEqual(code, 422, a)

    def test_the_copilot_cannot_make_owner_decisions(self):
        run_step(self.S, self.pid, 'direction:1'); run_step(self.S, self.pid, 'direction_check')
        st = self.S.state(self.pid)
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'cp_gate', {'gate': 'G1', 'decision': 'approved', 'content_hash': A.current(st)['G1']['hash']}, actor='copilot')


class TestAuditRegressions(Env):
    def test_classic_route_cannot_act_as_the_copilot_or_forge_costs(self):          # audit D1, D2
        from director.studio import api as SA
        for action, args in (('cp_check', {'target': 'script', 'ref': 1, 'kind': 'merged', 'lines': {}}),
                             ('cp_ai_call', {'id': 'x', 'kind': 'fact_check', 'role': 'r', 'worker': 'mock', 'label': 'x', 'cost_usd': -10}),
                             ('cp_gate', {'gate': 'G1'})):
            code, r = SA.handle(self.var, {'project': self.pid, 'action': action, 'actor': 'reviewer', 'args': args})
            self.assertEqual(code, 422, (action, r))
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'cp_ai_call', {'id': 'y', 'kind': 'fact_check', 'role': 'r', 'worker': 'mock', 'label': 'x', 'cost_usd': -10}, actor='system')
        self.assertEqual(self.S.state(self.pid)['copilot']['ai']['spent_usd'], 0.0)
        # re-audit N2: on a Co-Pilot project the classic screens make no decisions (the gates own them)
        for action, args in (('take_decision', {'take': 'x', 'decision': 'approved'}), ('finding_decision', {'finding': 'f', 'decision': 'dismissed', 'note': 'x'}),
                             ('script_decision', {'v': 1, 'decision': 'approved'}), ('run_voice', {})):
            code, r = SA.handle(self.var, {'project': self.pid, 'action': action, 'args': args})
            self.assertEqual(code, 422, (action, r)); self.assertIn('Co-Pilot', r['reason'])
        self.owner('cp_mode', {'mode': 'manual'})
        code, r = SA.handle(self.var, {'project': self.pid, 'action': 'take_decision', 'args': {'take': 'x', 'decision': 'approved'}})
        self.assertEqual((code, r['reason']), (422, 'unknown take'))                  # Manual: the classic rules apply again

    def test_an_ai_revised_line_gets_no_borrowed_sources(self):                    # re-audit N3
        run_step(self.S, self.pid, 'direction:1'); run_step(self.S, self.pid, 'direction_check')
        self.gate('G1')
        run_step(self.S, self.pid, 'script:'); run_step(self.S, self.pid, 'script_check:1')
        invented = 'باعت رولكس مليون ساعة أويستر في عامها الأول، وغاصت أويستر إلى عمق ألف متر.'
        orig = ai.MockWorker.k_revise_script
        ai.MockWorker.k_revise_script = lambda self, p: {'lines': {'l3': invented}, 'why': 'MOCK AI: invented a sentence, cited nothing'}
        try:
            run_step(self.S, self.pid, 'script_revise:1:auto')
        finally:
            ai.MockWorker.k_revise_script = orig
        run_step(self.S, self.pid, 'script_check:2')
        cp = self.S.state(self.pid)['copilot']
        self.assertEqual(O.script_meta(cp, 2)['claims']['l3'], [])
        x = O.merged_check(cp, 2)['lines']['l3']
        self.assertNotEqual(x['verdict'], 'supported'); self.assertIn(x['severity'], ('critical', 'major'))

    def test_an_owner_edited_line_gets_no_borrowed_sources(self):                  # audit D3
        self.to_g2()
        self.owner('cp_line_edit', {'line': 'l3', 'text': 'باعت رولكس مليون ساعة أويستر في عامها الأول، وغاصت أويستر إلى عمق ألف متر.'})
        run_step(self.S, self.pid, 'script_check:3')
        x = O.merged_check(self.S.state(self.pid)['copilot'], 3)['lines']['l3']
        self.assertEqual(x['claims'], []); self.assertEqual(x['sources'], [])
        self.assertIn(x['severity'], ('critical', 'major'))
        with self.assertRaises(Refused): self.gate('G2', overrides={'l3': 'c1'})

    def test_voice_reject_points_to_the_word_tools_and_style_feedback_reaches_a_person(self):   # audit D6
        self.to_g3()
        with self.assertRaises(Refused): self.gate('G3', decision='rejected', note='the names sound wrong')
        st = self.S.state(self.pid)
        self.S.act(self.pid, 'cp_style', {'n': 1, 'brief': st['art'].get('brief'), 'registry': 1, 'file': 'x', 'recommended': 'paper-story', 'reasons': {},
                                          'directions': [{'id': 'paper-story', 'version': 1, 'name': 'P', 'ready': True, 'board': None, 'params_hash': 'h'}]}, actor='copilot')
        self.gate('G4', decision='changes_requested', note='warmer colours please')
        k = run_step(self.S, self.pid, 'feedback:', first=False)
        ex = self.S.state(self.pid)['copilot']['exceptions'][-1]
        self.assertEqual((ex['kind'], ex['status']), ('owner_feedback', 'open'))

    def test_approved_in_manual_can_be_confirmed_at_gate_2(self):                   # audit D7
        self.to_g2()
        self.owner('cp_mode', {'mode': 'manual'})
        v = self.S.state(self.pid)['scripts'][-1]['v']
        self.S.act(self.pid, 'script_decision', {'v': v, 'decision': 'approved'})
        self.owner('cp_mode', {'mode': 'copilot'})
        self.gate('G2')
        self.assertTrue(A.validity(self.S.state(self.pid))['G2']['valid'])


class TestExceptionsAndControls(Env):
    def test_exception_pauses_and_the_decision_resumes_but_an_owner_pause_stays(self):
        self.S.act(self.pid, 'cp_exception', {'id': 'ex-1', 'kind': 'unfixable', 'scene': 'l5', 'title': 't', 'options': ['accept_best', 'manual'], 'pause': True}, actor='copilot')
        self.assertEqual(self.S.state(self.pid)['copilot']['run'], 'paused')
        with self.assertRaises(Refused): self.owner('cp_exception_decision', {'id': 'ex-1', 'decision': 'accept_best'})   # needs a reason
        self.owner('cp_exception_decision', {'id': 'ex-1', 'decision': 'accept_best', 'note': 'fine as it is'})
        self.assertEqual(self.S.state(self.pid)['copilot']['run'], 'running')
        self.owner('cp_control', {'op': 'pause'})
        self.S.act(self.pid, 'cp_exception', {'id': 'ex-2', 'kind': 'unfixable', 'scene': 'l6', 'title': 't', 'options': ['accept_best'], 'pause': True}, actor='copilot')
        self.owner('cp_exception_decision', {'id': 'ex-2', 'decision': 'accept_best', 'note': 'fine as it is'})
        self.assertEqual(self.S.state(self.pid)['copilot']['run'], 'paused')

    def test_a_failed_step_blocks_until_the_owner_resumes(self):
        jobs.FAIL_NEXT['copilot'] = 'injected failure'
        p = O.plan(self.S, self.pid)
        s = p['step']
        jobs.start(self.S, self.pid, 'copilot', s.stage, s.what, s.units, s.fn, {'key': s.key, **s.args}, sync=True)
        p = O.plan(self.S, self.pid)
        self.assertIsNone(p['step']); self.assertEqual(p['blocked'][0]['key'], s.key)
        self.owner('cp_control', {'op': 'retry', 'key': s.key})
        self.assertEqual(O.plan(self.S, self.pid)['step'].key, s.key)    # the owner asked: tried again, once

    def test_interrupted_work_is_redone_without_duplicates(self):
        run_step(self.S, self.pid, 'direction:1')
        n = len(self.S.state(self.pid)['copilot']['directions'])
        # a job that was running when the server stopped: a 'running' event with no live thread
        self.S.act(self.pid, 'job', {'id': 'j-copilot-dead', 'kind': 'copilot', 'stage': 'direction', 'what': 'x', 'state': 'running',
                                     'args': {'key': 'direction_check:1'}}, actor='system')
        st = self.S.state(self.pid)
        self.assertEqual(st['jobs'][-1]['state'], 'interrupted')
        self.assertEqual(O.plan(self.S, self.pid, st)['step'].key, 'direction_check:1')
        self.assertEqual(len(st['copilot']['directions']), n)


class TestVoiceAndAssets(Env):
    def test_speed_and_pause_make_a_labelled_new_take_and_keep_the_original(self):
        self.to_g3()
        st = self.S.state(self.pid)
        t0 = st['voice']['lines']['l5']['take']
        self.owner('cp_voice_adjust', {'line': 'l5', 'speed': 1.1, 'pause_before': 0.3})
        run_step(self.S, self.pid, 'adjust:')
        st = self.S.state(self.pid)
        t1 = st['voice']['lines']['l5']['take']
        self.assertNotEqual(t0, t1)
        self.assertIn(t0, st['voice']['takes'])
        nt, ot = st['voice']['takes'][t1], st['voice']['takes'][t0]
        self.assertIn('processed locally', nt['label'])
        self.assertAlmostEqual(nt['words'][0]['s'], 0.3 + ot['words'][0]['s'] / 1.1, places=2)
        with self.assertRaises(Refused): self.owner('cp_voice_adjust', {'line': 'l5', 'speed': 2.0})

    def test_owner_pronunciation_correction_is_a_rule_for_the_draft_voice(self):
        self.to_g3()
        self.owner('cp_pron', {'word': 'أويستر', 'respell': 'أُويْسْتَر', 'lines': ['l6']})
        st = self.S.state(self.pid)
        e = st['copilot']['pron'][-1]
        self.assertEqual((e['source'], e['status']), ('owner', 'approved'))
        self.assertTrue(any(r['id'] == e['rule']['id'] for r in st['voice']['rules']))
        old = st['voice']['lines']['l6']['take']
        k = run_step(self.S, self.pid, 'respell:')                              # the correction is recorded again (audit D5)
        st = self.S.state(self.pid)
        new = [t for t in st['voice']['by_line']['l6'] if t != old]
        self.assertTrue(new and 'أُويْسْتَر' in st['voice']['takes'][new[-1]]['spoken'], k)
        self.assertEqual(st['voice']['lines']['l5']['take'], st['voice']['lines']['l5']['take'])
        others = {l: x['take'] for l, x in st['voice']['lines'].items() if l != 'l6'}
        self.assertTrue(all(len(st['voice']['by_line'][l]) == 1 for l in others if 'أويستر' not in st['voice']['lines'][l]['text']))

    def test_a_picture_is_never_used_without_licence_evidence(self):
        png = (ROOT / 'vendor/paper-story/tk-logo-512.png').read_bytes()
        import base64
        self.owner('upload', {'data': base64.b64encode(png).decode(), 'name': 'w.png', 'slot': 'wilsdorf_portrait', 'scene': 'l6', 'use': 'evidence'})
        st = self.S.state(self.pid)
        a = list(st['copilot']['assets'].values())[0]
        self.assertEqual(a['status'], 'unverified')
        bs = {'beat': 'person_real', 'banner': 'هانس فيلسدورف', 'default': 'neutral_placeholder', 'concepts': {'neutral_placeholder': {'label': 'x'}}, '_id': 'l6'}
        style = styles.get('paper-story')
        self.assertEqual(styles.choose(style, bs, {})['technique'], 'kinetic_type')          # a name card, never a placeholder person
        with self.assertRaises(Refused): self.owner('cp_asset', {'op': 'licence', 'id': a['id'], 'licence': 'licensed', 'evidence': 'trust me'})
        with self.assertRaises(Refused): self.owner('cp_asset', {'op': 'licence', 'id': a['id'], 'licence': 'owner_owned'})
        # re-audit D12: a made-up site, or the picture itself, is not licence evidence; random bytes are not a picture
        with self.assertRaises(Refused): self.owner('cp_asset', {'op': 'licence', 'id': a['id'], 'licence': 'licensed', 'evidence': 'https://a.bc'})
        with self.assertRaises(Refused): self.owner('cp_asset', {'op': 'licence', 'id': a['id'], 'licence': 'licensed', 'evidence_file': a['file']})
        with self.assertRaises(Refused):
            self.owner('upload', {'data': base64.b64encode(b'\x89PNG\r\n\x1a\n' + os.urandom(4096)).decode(), 'name': 'x.png', 'slot': 's', 'scene': 'l6', 'use': 'evidence'})
        self.owner('cp_asset', {'op': 'licence', 'id': a['id'], 'licence': 'licensed', 'evidence': 'https://example.org/licence-page'})
        st = self.S.state(self.pid)
        a = list(st['copilot']['assets'].values())[0]
        self.assertEqual(a['status'], 'verified')
        self.assertEqual(styles.choose(style, bs, {a['slot']: a})['technique'], 'archival_collage')


class TestScenesRules(unittest.TestCase):
    def test_opening_scene_shows_its_words_from_frame_zero(self):
        b = {'scene': 'h', 'opening': True, 'technique': 'kinetic_type', 'params': {'lines': [{'text': 'أول ساعة', 'at': 0.0, 'in': 'slam'}]},
             'theme': 'tk-bone', 'text_scale': 1.0, 'owner_changes': {}, 'banner': None, 'dur': 4, 'line': 'x'}
        sc = SC.visual(SC.apply(b, {}), 'timekeeper')
        self.assertNotIn('in', sc['elements'][0])
        self.assertIsNone(sc['banner'])                                   # explicit: no banner carried over from anywhere

    def test_safe_fixes_exclude_words_and_style(self):
        self.assertFalse({'banner', 'theme', 'text'} & SC.SAFE_AI)


class TestPaidLocks(Env):
    def test_paid_gate_cannot_pass_here_and_final_generation_is_refused(self):
        with self.assertRaises(Refused): self.S.act(self.pid, 'final_generate', {})
        code, r = CA.handle(self.var, {'project': self.pid, 'action': 'final_generate', 'args': {}})
        self.assertEqual(code, 422)

    def test_mock_paid_provider_rejects_unauthorized_outdated_reused_and_over_budget(self):
        from director.voice.plan import build_plan
        from director.library import Library
        led = Ledger(self.var / 'l.sqlite'); store = TakeStore(self.var / 'takes')
        voice = {'provider': 'elevenlabs', 'voice_id': 'v', 'model': 'm', 'settings': {}, 'seed': 1, 'output_format': 'mp3_44100_128'}
        plan = build_plan('p', [{'id': 'l1', 'text': 'نص قصير'}], voice, Library([], name='x'), store)
        gw = PaidGateway(led, store, {'elevenlabs': ElevenLabsProvider(MockTransport())}, enabled=True)
        with self.assertRaises(PaidCallRefused): gw.run(plan, 'ap_none')                            # no approval
        aid = gw.approve(plan, 'owner')
        with self.assertRaises(PaidCallRefused): gw.run(plan, aid)                                  # no budget
        led.set_budget('p', 'elevenlabs', 3)
        with self.assertRaises(PaidCallRefused): gw.run(plan, aid)                                  # over budget
        changed = dict(plan, items=[dict(plan['items'][0], provider_input='نص آخر')])
        with self.assertRaises(PaidCallRefused): gw.run(changed, aid)                               # plan changed after approval
        led.set_budget('p', 'elevenlabs', 1000)
        gw.run(plan, aid)
        with self.assertRaises(PaidCallRefused): gw.run(plan, aid)                                  # single use
        off = PaidGateway(led, store, {'elevenlabs': ElevenLabsProvider(MockTransport())})
        with self.assertRaises(PaidCallRefused): off.run(plan, gw.approve(plan, 'owner'))         # disabled in this environment


if __name__ == '__main__':
    unittest.main()
