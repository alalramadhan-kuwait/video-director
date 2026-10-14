"""Studio rules: one brand per project, versions are immutable, corrections touch one word, selecting is not approving,
statuses come only from decisions, repeated requests are recorded once, and nothing reaches a paid provider.
The draft voice runs in 'offline-mock' mode (a tone per word); the network is blocked for the whole run."""
from tests import _guard  # noqa: F401
import ast, json, os, stat, tempfile, unittest
from pathlib import Path

os.environ['VD_DRAFT_VOICE'] = 'offline-mock'
from director.studio.store import Studio, Refused
from director.studio import voice, jobs, gate, art, checks, api
from director.ledger import Ledger
from director.voice.takes import TakeStore
from director.voice.gateway import PaidGateway, ElevenLabsProvider, PaidCallRefused
from tests.test_voice import MockTransport

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = json.loads((ROOT / 'research/rolex-oyster.json').read_text(encoding='utf-8'))
SCRIPT = json.loads((ROOT / 'uat/rolex/script.json').read_text(encoding='utf-8'))
V2 = [{**l, 'text': SCRIPT['v2_changes'].get(l['id'], l['text'])} for l in SCRIPT['v1']]


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.S = Studio(Path(self.tmp.name))
        self.pid = self.S.act(None, 'create_project', {'title': 'Rolex Oyster', 'idea': 'the Oyster', 'brand': 'timekeeper'})['project']
        self.S.act(self.pid, 'research', {'data': RESEARCH}, 'research')

    def tearDown(self):
        for p in Path(self.tmp.name).rglob('*'):
            if p.is_file(): os.chmod(p, 0o644)
        self.tmp.cleanup()

    def approved_v2(self):
        self.S.act(self.pid, 'script_version', {'lines': V2})
        v = self.S.state(self.pid)['scripts'][-1]['v']
        self.S.act(self.pid, 'script_decision', {'v': v, 'decision': 'approved'})
        return v

    def voice_all(self):
        jobs.start(self.S, self.pid, 'voice', 'voice', 'draft voice', 13, voice.generate, sync=True)
        return self.S.state(self.pid)


class TestProject(Env):
    def test_brand_isolation(self):
        st = self.S.state(self.pid)
        self.assertEqual(st['identity']['profile'], 'timekeeper-luxury-doc')
        self.assertTrue(all(k.startswith('tk-') for k in st['identity']['palette']))
        self.assertNotIn('diabetes', json.dumps(st['identity']).lower())
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'set_identity', {'profile': 'diabetes-history-sci'})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'set_voice', {'voice': 'bram'})           # a Diabetes History voice

    def test_final_voice_needs_authorization_for_a_new_film(self):
        v = self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})['result']['voice']
        self.assertEqual(v['status'], 'needs_authorization')
        self.assertIn('royal-oak', v['why'])
        self.assertEqual(self.S.act(self.pid, 'set_voice', {'voice': 'ali_clone'})['result']['voice']['status'], 'needs_authorization')

    def test_reopen_replays_the_same_state(self):
        self.approved_v2()
        a = self.S.state(self.pid)
        b = Studio(Path(self.tmp.name)).state(self.pid)              # a new process opening the same files
        self.assertEqual([(s['v'], s['status']) for s in a['scripts']], [(s['v'], s['status']) for s in b['scripts']])

    def test_same_request_twice_is_recorded_once(self):
        n = len(self.S.events(self.pid))
        r1 = self.S.act(self.pid, 'script_version', {'lines': V2}, request_id='rq-1')
        r2 = self.S.act(self.pid, 'script_version', {'lines': V2}, request_id='rq-1')
        self.assertEqual((r1['status'], r2['status']), ('recorded', 'duplicate'))
        self.assertEqual(len(self.S.events(self.pid)), n + 1)

    def test_a_file_on_disk_never_approves_anything(self):
        st0 = self.S.state(self.pid)
        fake = self.S.pdir(self.pid) / 'blobs' / 'approved-take.mp3'
        fake.write_bytes(b'ID3 not a decision')
        (self.S.pdir(self.pid) / 'final-takes').mkdir(exist_ok=True)
        st1 = self.S.state(self.pid)
        self.assertEqual(st0['steps'], st1['steps'])
        self.assertEqual(st1['voice']['takes'], {})


class TestScript(Env):
    def test_claim_guard_blocks_approval(self):
        r = self.S.act(self.pid, 'script_version', {'lines': SCRIPT['v1']})['result']
        self.assertTrue(any(c['code'] == 'CLAIM_UNSUPPORTED' and c['line'] == 'l6' for c in r['checks']))
        self.assertFalse(any(c['code'] == 'CLAIM_UNSUPPORTED' and c['line'] == 'l1' for c in r['checks']), 'attributed («يقولون») is allowed')
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'script_decision', {'v': 1, 'decision': 'approved'})

    def test_typo_detected_and_corrected_without_touching_anything_else(self):
        self.S.act(self.pid, 'script_version', {'lines': V2})
        v3 = [{**l, 'text': l['text'].replace('فيلسدورف', 'فيلسدروف')} if l['id'] == 'l6' else l for l in V2]
        r = self.S.act(self.pid, 'script_version', {'lines': v3})['result']
        sp = [c for c in r['checks'] if c['code'] == 'SPELLING']
        self.assertEqual([(c['line'], c['word'], c['suggestion']) for c in sp], [('l6', 'فيلسدروف', 'فيلسدورف')])
        before = {f: f.read_bytes() for f in (self.S.pdir(self.pid) / 'blobs').glob('*.json')}
        f = self.S.act(self.pid, 'flag_word', {'v': 2, 'line': 'l6', 'wi': sp[0]['wi'], 'kind': 'spelling', 'note': 'swapped'})['result']
        c = self.S.act(self.pid, 'apply_correction', {'flag': f['flag'], 'replacement': 'فيلسدورف'})['result']
        self.assertEqual(c['diff'], [{'line': 'l6', 'op': 'replace', 'at': c['diff'][0]['at'], 'old': 'فيلسدروف', 'new': 'فيلسدورف'}])
        st = self.S.state(self.pid)
        new = self.S.read_json(self.pid, st['scripts'][-1]['file'])['lines']
        self.assertEqual(new, V2)                                         # exactly the clean text again
        for p, data in before.items():                                    # earlier versions: same bytes, read-only
            self.assertEqual(p.read_bytes(), data)
            self.assertFalse(os.stat(p).st_mode & stat.S_IWUSR)
        self.assertEqual(st['flags'][0]['status'], 'applied')

    def test_old_drafts_are_superseded_and_approval_is_final(self):
        self.S.act(self.pid, 'script_version', {'lines': V2})
        self.S.act(self.pid, 'script_version', {'lines': V2})
        st = self.S.state(self.pid)
        self.assertEqual([s['status'] for s in st['scripts']], ['superseded', 'draft'])
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'script_decision', {'v': 1, 'decision': 'approved'})
        self.S.act(self.pid, 'script_decision', {'v': 2, 'decision': 'approved'})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'script_decision', {'v': 2, 'decision': 'rejected', 'note': 'x'})

    def test_hook_selection_makes_a_new_version_that_still_needs_approval(self):
        self.approved_v2()
        hooks = json.loads((ROOT / 'uat/rolex/hooks.json').read_text(encoding='utf-8'))
        self.S.act(self.pid, 'hooks', {'options': hooks['options'], 'recommended': 'H1', 'reasons': hooks['reasons']})
        r = self.S.act(self.pid, 'hook_select', {'hook': 'H2'})['result']
        st = self.S.state(self.pid)
        self.assertEqual(st['hooks']['selected'], 'H2')
        self.assertEqual(st['scripts'][-1]['status'], 'draft')
        self.assertEqual(self.S.read_json(self.pid, st['scripts'][-1]['file'])['lines'][0]['id'], 'h')
        self.assertEqual(st['steps'][2]['state'], 'waiting_review')         # payoff not confirmed yet


class TestVoice(Env):
    def test_draft_voice_flag_fix_one_line_and_decisions(self):
        self.approved_v2()
        st = self.voice_all()
        self.assertEqual(len(st['voice']['takes']), 13)
        t9 = st['voice']['takes'][st['voice']['by_line']['l9'][0]]
        self.assertTrue(t9['label'].startswith('DRAFT VOICE'))
        wi = next(i for i, w in enumerate(t9['words']) if 'غلايتسه' in w['w'])
        with self.assertRaises(Refused):                                   # flag a word you did not play
            self.S.act(self.pid, 'voice_flag', {'take': t9['id'], 'wi': wi, 'kind': 'vowel'})
        f = self.S.act(self.pid, 'voice_flag', {'take': t9['id'], 'wi': wi, 'kind': 'vowel', 'played': True, 'note': 'stress'})['result']
        self.S.act(self.pid, 'voice_fix', {'vflag': f['vflag'], 'respell': 'غْلايْتْسَهْ'})                 # same number of words
        jobs.start(self.S, self.pid, 'voice', 'voice', 'fix', 1, voice.fix_line, {'line': 'l9', 'vflag': f['vflag']}, sync=True)
        st = self.S.state(self.pid)
        self.assertEqual(len(st['voice']['by_line']['l9']), 2)
        self.assertTrue(all(len(v) == 1 for k, v in st['voice']['by_line'].items() if k != 'l9'))
        self.assertTrue(st['jobs'][-1]['out']['others_unchanged'])
        # the offline mock voice makes the same tones for the same number of words: the 'fix' changed nothing audible
        self.assertTrue(st['jobs'][-1]['out']['no_effect'])
        self.assertEqual(st['voice']['flags'][0]['status'], 'fix_no_effect')
        new = st['voice']['takes'][st['voice']['by_line']['l9'][1]]
        self.assertIn('غْلايْتْسَهْ', new['spoken'])
        self.assertNotIn('غْلايْتْسَهْ', self.S.read_json(self.pid, st['scripts'][-1]['file'])['lines'][8]['text'], 'the script is never edited')
        with self.assertRaises(Refused):                                   # no listening proof
            self.S.act(self.pid, 'take_decision', {'take': new['id'], 'decision': 'approved'})
        with self.assertRaises(Refused):                                   # 'ended' alone (a seek to the end) is not listening
            self.S.act(self.pid, 'take_decision', {'take': new['id'], 'decision': 'approved', 'playback': {'ended': True, 'listened_s': 0.4}})
        w = new['words'][wi]; L = new['seconds']
        with self.assertRaises(Refused):                                   # the same opening part four times is not 80 % of the take
            self.S.act(self.pid, 'take_decision', {'take': new['id'], 'decision': 'approved', 'playback': {'listened_s': L, 'covered': [[0, 0.25 * L]] * 4}})
        with self.assertRaises(Refused):                                   # 80 % heard, but not the fixed word
            self.S.act(self.pid, 'take_decision', {'take': new['id'], 'decision': 'approved', 'playback': {'covered': [[0, w['s'] - 0.01], [w['e'] + 0.01, L]]}})
        with self.assertRaises(Refused):                                   # a total without the parts heard is not enough for a re-take
            self.S.act(self.pid, 'take_decision', {'take': new['id'], 'decision': 'approved', 'playback': {'listened_s': L}})
        self.S.act(self.pid, 'take_decision', {'take': new['id'], 'decision': 'approved', 'playback': {'covered': [[0, L]]}})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'take_decision', {'take': new['id'], 'decision': 'rejected', 'playback': {'covered': [[0, L]]}})

    def test_interrupted_job_is_shown_as_interrupted(self):
        self.approved_v2()
        self.S.act(self.pid, 'job', {'id': 'j-voice-x', 'kind': 'voice', 'stage': 'voice', 'what': 'draft voice', 'state': 'running', 'args': {}}, 'system')
        st = Studio(Path(self.tmp.name)).state(self.pid)                  # a restarted server has no live thread
        self.assertEqual(st['jobs'][-1]['state'], 'interrupted')
        self.assertEqual(st['steps'][3]['state'], 'interrupted')

    def test_missing_voice_file_stops_the_render_with_a_clear_message(self):
        from director.studio import storyboard
        self.approved_v2()
        st = self.voice_all()
        doc = {'scenes': [{'id': 'l3', 'technique': 'kinetic_type', 'params': {'lines': [{'text': 'x'}]}, 'theme': 'tk-bone', 'dur': 4,
                           'banner': None, 'transition': 'cut', 'take': st['voice']['by_line']['l3'][0], 'line': 'x'}], 'endcard': None}
        wav = self.S.path(self.pid, st['voice']['takes'][doc['scenes'][0]['take']]['wav'])
        os.chmod(wav, 0o644); wav.unlink()                                   # the media disappeared (disk, restore, mistake)
        with self.assertRaisesRegex(FileNotFoundError, 'voice file for l3 is missing'):
            storyboard.engine_storyboard(self.S, self.pid, doc, Path(self.tmp.name) / 'work')

    def test_stale_failure_is_cleared_by_a_later_successful_run(self):
        self.approved_v2()
        for jid, state in (('j-render-1', 'failed'), ('j-render-2', 'finished')):
            self.S.act(self.pid, 'job', {'id': jid, 'kind': 'render', 'stage': 'draft', 'what': 'draft render', 'state': state, 'error': 'x'}, 'system')
        api._STUDIOS.clear()
        v = api.view(self.tmp.name, self.pid)
        self.assertFalse([b for b in v['blockers'] if 'render' in b['what']])

    def test_dead_run_is_not_shown_as_running_with_an_eta(self):
        self.approved_v2()
        with self.S.log.task(self.pid, 'draft voice', 13, stage='voice') as t:
            for _ in range(4): t.unit()
            self.S.act(self.pid, 'job', {'id': 'j-voice-y', 'kind': 'voice', 'stage': 'voice', 'what': 'draft voice', 'state': 'running', 'args': {}}, 'system')
            api._STUDIOS.clear()
            v = api.view(self.tmp.name, self.pid)          # read while the 'server' has no live job
            self.assertEqual(v['running'], [])
            r = [x for x in v['runs'] if x['task'] == 'draft voice'][-1]
            self.assertEqual((r['state'], r['eta_s']), ('interrupted', None))

    def test_failed_job_records_the_error_and_changes_nothing(self):
        self.approved_v2()
        jobs.FAIL_NEXT['voice'] = 'simulated'
        jobs.start(self.S, self.pid, 'voice', 'voice', 'draft voice', 13, voice.generate, sync=True)
        st = self.S.state(self.pid)
        self.assertEqual(st['jobs'][-1]['state'], 'failed')
        self.assertEqual(st['voice']['takes'], {})
        self.assertEqual(self.S.log.runs(self.pid)[-1]['state'], 'failed')


class TestAuditDefects(Env):
    """Regression tests for the independent audit (var/audit/AUDIT_REPORT.md, D-01..D-17)."""

    def _hooks(self):
        hooks = json.loads((ROOT / 'uat/rolex/hooks.json').read_text(encoding='utf-8'))
        self.S.act(self.pid, 'hooks', {'options': hooks['options'], 'recommended': 'H1', 'reasons': hooks['reasons']})

    def test_D01_takes_for_old_text_are_stale_everywhere(self):
        self.approved_v2(); self._hooks()
        self.S.act(self.pid, 'hook_select', {'hook': 'H1'})
        self.S.act(self.pid, 'script_decision', {'v': 2, 'decision': 'approved'})
        st = self.voice_all()
        for ln, x in st['voice']['lines'].items():
            self.S.act(self.pid, 'take_decision', {'take': x['take'], 'decision': 'approved', 'playback': {'listened_s': 99}})
        self.assertEqual(self.S.state(self.pid)['steps'][3]['state'], 'approved')
        self.S.act(self.pid, 'hook_select', {'hook': 'H2'})                       # new first line → v3
        self.S.act(self.pid, 'script_decision', {'v': 3, 'decision': 'approved'})
        st = self.S.state(self.pid)
        self.assertEqual(st['voice']['lines']['h']['status'], 'stale')
        self.assertNotEqual(st['steps'][3]['state'], 'approved')
        g = gate.plan(self.S, self.pid) if st['voice_profile'] else None
        self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})
        self.assertTrue(any('current text' in b for b in gate.plan(self.S, self.pid)['blockers']))
        jobs.start(self.S, self.pid, 'voice', 'voice', 'draft voice', 1, voice.generate, sync=True)   # only the stale line
        st = self.S.state(self.pid)
        self.assertEqual(st['voice']['lines']['h']['status'], 'candidate')
        self.assertEqual(sum(len(v) for v in st['voice']['by_line'].values()), 14)

    def test_D02_claim_rule_catches_paraphrases_and_misplaced_attribution(self):
        R = RESEARCH
        claims = lambda t: [c for c in checks.check_version([{'id': 'x', 'text': t}], R, []) if c['code'] == 'CLAIM_UNSUPPORTED']
        for t in ('كانت أويستر أولَ ساعةِ يدٍ مضادةٍ للماء في العالم.', 'لم يسبق أحدٌ رولكس إلى ساعة اليد المقاومة للماء.',
                  'يقولون إنها جميلة، لكن الحقيقة أن رولكس صنعت أول ساعة يد مقاومة للماء.'):
            self.assertTrue(claims(t), t)
        for t in (SCRIPT['v1'][0]['text'], 'رولكس لم تخترع الساعة المقاومة للماء… لكنها جعلت العالم يثق بها.',
                  'لم تكن أويستر أول ساعة مقاومة للماء.', 'قبل أويستر بسنوات، سبقتها ساعات يد مقاومة للماء.',
                  'وبعد شهر، نشرت رولكس القصة في إعلانٍ على الصفحة الأولى لصحيفة ديلي ميل.'):
            self.assertFalse(claims(t), t)

    def test_D02_colon_after_attribution_keeps_it_attributed(self):
        from director.studio import checks
        c6 = next(c for c in RESEARCH['claims'] if c['id'] == 'c6')
        self.assertEqual(checks._claim_hits('يقولون: أول ساعة مقاومة للماء؟', c6), [])        # the corrected hook card
        self.assertEqual(checks._claim_hits('يقولون: أول ساعة\nمقاومة للماء؟', c6), [])
        self.assertTrue(checks._claim_hits('أول ساعة مقاومة للماء: يقولون', c6))                # attribution after the claim
        self.assertTrue(checks._claim_hits('كانت أويستر أولَ ساعةِ يدٍ مضادةٍ للماء في العالم', c6))

    def test_D02_round2_variants(self):
        claims = lambda t: [c for c in checks.check_version([{'id': 'x', 'text': t}], RESEARCH, []) if c['code'] == 'CLAIM_UNSUPPORTED']
        for t in ('وهذا ما جعل أويستر أول ساعة مقاومة للماء في التاريخ.', 'كانت أويستر ساعةً ثقيلة وأول ساعة مقاومة للماء.',
                  'كانت رولكس السبّاقة إلى الساعة المقاومة للماء.', 'أويستر ساعة لم تسبقها أي ساعة مقاومة للماء.',
                  'يقولون: إنها جميلة. أويستر أول ساعة مقاومة للماء.'):
            self.assertTrue(claims(t), t)
        for t in ('أول ما يدخل الماء إلى الساعة يأتي من التاج.', 'سبقتها ساعات مقاومة للماء من بورجيل وتافان.',
                  'يقولون: أول ساعة مقاومة للماء… والحقيقة أذكى من ذلك.', 'لم تكن أويستر أول ساعة مقاومة للماء.'):
            self.assertFalse(claims(t), t)

    def test_D02_override_needs_a_reason(self):
        self.S.act(self.pid, 'script_version', {'lines': SCRIPT['v1']})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'script_decision', {'v': 1, 'decision': 'approved', 'override': True})
        for junk in ('aaaaaaaaaaaa', 'ok ok ok ok ok', 'fine'):
            with self.assertRaises(Refused):                               # a reason, not 12 characters
                self.S.act(self.pid, 'script_decision', {'v': 1, 'decision': 'approved', 'override': True, 'note': junk})
        r = self.S.act(self.pid, 'script_decision', {'v': 1, 'decision': 'approved', 'override': True, 'note': 'UAT: testing the override path'})
        self.assertTrue(r['result']['override'])

    def test_D06_spelling_vocabulary_is_approved_text_only(self):
        typo = [{**l, 'text': l['text'].replace('غلايتسه', 'غلاتيسه')} for l in V2]
        sp = lambda r: [c for c in r['checks'] if c['code'] == 'SPELLING']
        r1 = self.S.act(self.pid, 'script_version', {'lines': typo})['result']
        self.assertTrue(sp(r1))
        r2 = self.S.act(self.pid, 'script_version', {'lines': typo})['result']   # same typo again in the next draft
        self.assertTrue(sp(r2), 'a typo in an unapproved draft must not become a known word')
        self.assertFalse([c for c in sp(r2) if c['word'].startswith('سبع')], 'سبعة (seven) is not a misspelling of ساعة')

    def test_D09_D13_blocked_and_rejected_concepts(self):
        c = {'id': 'l9-photo', 'scene': 'l9', 'technique': 'archival_collage', 'support': 'blocked: missing asset', 'params': {}, 'theme': 'tk-bone',
             'versions': [{'v': 1, 'stills': [], 'status': None}]}
        ok = {**c, 'id': 'l9-map', 'technique': 'map', 'support': 'rendered'}
        self.S.act(self.pid, 'art_concepts', {'scene': 'l9', 'concepts': [c, ok]}, 'system')
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'art_decision', {'concept': 'l9-photo', 'version': 1, 'decision': 'approved'})
        self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 1, 'decision': 'rejected'})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'art_select', {'concept': 'l9-map'})

    def test_D05_note_only_revision_waits_for_the_operator(self):
        c = {'id': 'l9-map', 'scene': 'l9', 'technique': 'map', 'support': 'rendered', 'params': {}, 'theme': 'tk-bone',
             'versions': [{'v': 1, 'stills': ['blobs/a.png'], 'status': None}]}
        self.S.act(self.pid, 'art_concepts', {'scene': 'l9', 'concepts': [c]}, 'system')
        code, r = api.handle(self.tmp.name, {'project': self.pid, 'action': 'art_modify', 'args': {'concept': 'l9-map', 'changes': {}, 'note': 'move the label'}})
        api._STUDIOS.clear()
        self.assertNotIn('job', r)
        st = Studio(Path(self.tmp.name)).state(self.pid)
        self.assertEqual(st['art']['requests'][0]['status'], 'waiting_operator')
        self.assertEqual(len(st['art']['concepts']['l9-map']['versions']), 1)

    def test_newer_version_of_approved_art_replaces_it_in_one_step(self):
        c = {'id': 'l9-map', 'scene': 'l9', 'technique': 'map', 'support': 'rendered', 'params': {}, 'theme': 'tk-bone',
             'versions': [{'v': 1, 'stills': ['blobs/a.png'], 'status': None}]}
        other = {**c, 'id': 'l9-kinetic', 'technique': 'kinetic_type'}
        self.S.act(self.pid, 'art_concepts', {'scene': 'l9', 'concepts': [c, other]}, 'system')
        self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 1, 'decision': 'approved'})
        self.S.act(self.pid, 'art_modify', {'concept': 'l9-map', 'changes': {'text_size': '1.2'}})
        self.S.act(self.pid, 'art_revision', {'concept': 'l9-map', 'version': {'v': 2, 'stills': ['blobs/b.png'], 'status': None}}, 'system')
        self.assertEqual(self.S.state(self.pid)['art']['approved']['l9'], {'concept': 'l9-map', 'version': 1})   # v1 stays in use
        with self.assertRaises(Refused):                                   # another concept still needs a withdraw first
            self.S.act(self.pid, 'art_decision', {'concept': 'l9-kinetic', 'version': 1, 'decision': 'approved'})
        self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 2, 'decision': 'approved'})
        st = self.S.state(self.pid)
        self.assertEqual(st['art']['approved']['l9'], {'concept': 'l9-map', 'version': 2})
        self.assertEqual([v['status'] for v in st['art']['concepts']['l9-map']['versions']], ['replaced', 'approved'])
        with self.assertRaises(Refused):                                   # going back is a withdraw, not a silent swap
            self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 1, 'decision': 'approved'})

    def test_D10_D14_storyboard_needs_approval_and_decisions_are_final(self):
        self.approved_v2()
        self.S.act(self.pid, 'art_brief', {'brief': json.loads((ROOT / 'uat/rolex/art_brief.json').read_text(encoding='utf-8'))})
        self.voice_all()
        from director.studio import storyboard
        sb = storyboard.build(self.S, self.pid)
        st = self.S.state(self.pid)
        self.assertEqual(st['steps'][5]['state'], 'waiting_review')
        self.assertTrue(any('not reviewed' in w for w in sb['warnings']))
        self.assertTrue(any('PLACEHOLDER' in w for w in sb['warnings']))         # l6 silhouette
        with self.assertRaises(Refused):                                          # takes not approved yet is fine; versions must match
            self.S.act(self.pid, 'storyboard_decision', {'v': 99, 'decision': 'approved'})
        self.S.act(self.pid, 'storyboard_decision', {'v': sb['v'], 'decision': 'approved'})
        self.assertEqual(self.S.state(self.pid)['steps'][5]['state'], 'approved')
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'storyboard_decision', {'v': sb['v'], 'decision': 'changes_requested'})
        self.S.act(self.pid, 'research_decision', {'decision': 'approved'})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'research_decision', {'decision': 'changes_requested'})

    def test_N1_opening_visual_follows_the_selected_hook(self):
        self.approved_v2(); self._hooks()
        self.S.act(self.pid, 'art_brief', {'brief': json.loads((ROOT / 'uat/rolex/art_brief.json').read_text(encoding='utf-8'))})
        from director.studio import storyboard
        for hook, tech in (('H2', 'paper_cut'), ('H1', 'kinetic_type')):
            self.S.act(self.pid, 'hook_select', {'hook': hook})
            v = self.S.state(self.pid)['scripts'][-1]['v']
            self.S.act(self.pid, 'script_decision', {'v': v, 'decision': 'approved'})
            sb = storyboard.build(self.S, self.pid)
            h = sb['scenes'][0]
            self.assertEqual((h['id'], h['technique']), ('h', tech), hook)
        self.assertIsNone(h['banner'])                                       # H1's card carries its own text
        self.S.act(self.pid, 'hook_select', {'hook': 'H2'})
        v = self.S.state(self.pid)['scripts'][-1]['v']
        self.S.act(self.pid, 'script_decision', {'v': v, 'decision': 'approved'})
        h = storyboard.build(self.S, self.pid)['scenes'][0]
        self.assertEqual(h['banner'], 'عشر ساعات في بحرٍ بارد')              # a picture hook shows its on-screen text
        self.assertIn('hook H2', h['status']['art'])

    def test_D03_word_window_decides_whether_the_fix_changed_the_flagged_word(self):
        import numpy as np
        sr = voice.SR; t = np.arange(sr * 3) / sr
        a = 0.3 * np.sin(2 * np.pi * 180 * t)
        w = {'s': 1.0, 'e': 1.6}
        b = a.copy(); b[int(2.2 * sr):int(2.6 * sr)] *= 0.2                  # elsewhere changed, flagged word identical
        self.assertLess(voice.word_change(a, b, w, w), voice.WORD_SAME)
        c = a.copy(); c[int(1.0 * sr):int(1.6 * sr)] = 0.3 * np.sin(2 * np.pi * 260 * t[int(1.0 * sr):int(1.6 * sr)])
        self.assertGreater(voice.word_change(a, c, w, w), voice.WORD_SAME)   # the flagged word itself changed
        shifted = np.concatenate([np.zeros(int(.02 * sr)), a])[:len(a)]      # same sound 20 ms later
        self.assertLess(voice.word_change(a, shifted, w, w), voice.WORD_SAME)

    def test_D08_gate_blockers_are_actionable(self):
        self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})
        self.approved_v2()
        b0 = gate.plan(self.S, self.pid)['blockers']
        self.assertTrue(any('royal-oak' in b for b in b0) and any('proposed' in b for b in b0) and any('budget' in b for b in b0))
        self.S.act(self.pid, 'authorize_voice', {'note': 'owner: OK for the Rolex film'})
        for t in RESEARCH['terms']:
            self.S.act(self.pid, 'term_decision', {'surface': t['ar'], 'decision': 'latin' if t['final'] == 'latin' else 'arabic'})
        self.S.act(self.pid, 'set_budget', {'characters': 5000})
        g = gate.plan(self.S, self.pid)
        b1 = ' | '.join(g['blockers'])
        self.assertNotIn('royal-oak', b1); self.assertNotIn('proposed', b1); self.assertNotIn('budget', b1)
        self.assertIn('Rolex', ' '.join(i['provider_input'] for i in g['items']))       # approved Latin names are used
        self.assertIn('disabled in this environment', b1)

    def test_round2_voice_authorization_survives_switching_back(self):
        self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})
        self.S.act(self.pid, 'authorize_voice', {'note': 'owner: OK for the Rolex film'})
        self.S.act(self.pid, 'set_voice', {'voice': 'ali_recorded'})
        self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})
        self.assertEqual(self.S.state(self.pid)['voice_profile']['status'], 'usable')

    def test_round2_unreviewed_draft_blocks_and_stale_plan_is_not_shown_as_current(self):
        self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})
        self.approved_v2()
        self.S.act(self.pid, 'render', {'id': 'r1', 'state': 'ok', 'seconds': 10, 'file': 'x.mp4'}, 'system')
        b = gate.plan(self.S, self.pid)['blockers']
        self.assertTrue(any('not been checked by the independent reviewer' in x for x in b), b)
        api._STUDIOS.clear()
        v = api.view(Path(self.tmp.name), self.pid)
        self.assertFalse(v['gate']['plan_stale'])
        self.assertTrue(any('budget' in x['what'] for x in v['blockers']))
        import time; time.sleep(1.1)
        Studio(Path(self.tmp.name)).act(self.pid, 'set_budget', {'characters': 5000})
        api._STUDIOS.clear()
        v = api.view(Path(self.tmp.name), self.pid)
        self.assertTrue(v['gate']['plan_stale'])
        gate_items = [x['what'] for x in v['blockers'] if x['why'] == 'final gate']
        self.assertEqual(gate_items, [api.STALE_PLAN])                     # not the old 'no budget' blocker
        g = next(x for x in v['inbox_groups'] if x['key'] == 'gate')
        self.assertFalse(any('budget' in i['what'] for i in g['items']))

    def test_D17_recorded_voice_has_no_paid_plan(self):
        self.S.act(self.pid, 'set_voice', {'voice': 'ali_recorded'})
        self.approved_v2()
        g = gate.plan(self.S, self.pid)
        self.assertTrue(g['no_paid']); self.assertEqual(g['chars_total'], 0)


class TestArtAndReview(Env):
    def _concept(self):
        c = {'id': 'l9-map', 'scene': 'l9', 'technique': 'map', 'support': 'rendered', 'params': {}, 'theme': 'tk-graphite',
             'versions': [{'v': 1, 'stills': [], 'status': None}]}
        self.S.act(self.pid, 'art_concepts', {'scene': 'l9', 'concepts': [c, {**c, 'id': 'l9-photo', 'technique': 'archival_collage', 'support': 'blocked: missing asset'}]}, 'system')

    def test_round2_only_effective_changes_and_notes_reach_the_operator(self):
        brief = json.loads((ROOT / 'uat/rolex/art_brief.json').read_text(encoding='utf-8'))
        tl = brief['scenes']['l2']['concepts']['animated_timeline']
        self.assertNotIn('text_size:1.2', art.effective_changes('animated_timeline', tl, 'tk-bone'))
        mp = brief['scenes']['l9']['concepts']['map']
        self.assertTrue({'zoom:1.18', 'text_size:1.2'} <= set(art.effective_changes('map', mp, 'tk-bone')))   # a map can be pushed in
        c = {'id': 'l2-tl', 'scene': 'l2', 'technique': 'animated_timeline', 'support': 'rendered', 'params': tl, 'theme': 'tk-bone',
             'versions': [{'v': 1, 'stills': ['blobs/a.png'], 'status': None, 'params': tl, 'theme': 'tk-bone'}]}
        self.S.act(self.pid, 'art_concepts', {'scene': 'l2', 'concepts': [c]}, 'system')
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'art_modify', {'concept': 'l2-tl', 'changes': {'text_size': '1.2'}})
        self.S.act(self.pid, 'art_modify', {'concept': 'l2-tl', 'changes': {'theme': 'tk-ink'}, 'note': 'and put 1926 on its own line'})
        self.S.act(self.pid, 'art_revision', {'concept': 'l2-tl', 'version': {'v': 2, 'stills': ['blobs/b.png'], 'status': None}}, 'system')
        q = self.S.state(self.pid)['art']['requests'][-1]
        self.assertEqual((q['status'], q['version']), ('waiting_operator', 2))     # the note is not dropped

    def test_round2_pending_revision_of_approved_art_is_in_the_inbox(self):
        c = {'id': 'l9-map', 'scene': 'l9', 'technique': 'map', 'support': 'rendered', 'params': {}, 'theme': 'tk-bone',
             'versions': [{'v': 1, 'stills': ['blobs/a.png'], 'status': None}]}
        self.S.act(self.pid, 'art_concepts', {'scene': 'l9', 'concepts': [c]}, 'system')
        self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 1, 'decision': 'approved'})
        self.S.act(self.pid, 'art_revision', {'concept': 'l9-map', 'version': {'v': 2, 'stills': ['blobs/b.png'], 'status': None}}, 'system')
        api._STUDIOS.clear()
        v = api.view(Path(self.tmp.name), self.pid)
        items = [i['what'] for g in v['inbox_groups'] for i in g['items']]
        self.assertTrue(any('approve or reject v2' in i for i in items), items)

    def test_select_is_not_approve_and_withdraw_needs_a_reason(self):
        self._concept()
        self.S.act(self.pid, 'art_select', {'concept': 'l9-map'})
        st = self.S.state(self.pid)
        self.assertEqual(st['art']['selected'], {'l9': 'l9-map'}); self.assertEqual(st['art']['approved'], {})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'art_select', {'concept': 'l9-photo'})     # nothing to choose: blocked
        self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 1, 'decision': 'approved'})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 1, 'decision': 'withdrawn'})
        self.S.act(self.pid, 'art_decision', {'concept': 'l9-map', 'version': 1, 'decision': 'withdrawn', 'note': 'changed my mind'})
        st = self.S.state(self.pid)
        self.assertEqual(st['art']['approved'], {})
        self.assertEqual(st['art']['concepts']['l9-map']['versions'][0]['status'], 'withdrawn')

    def test_builders_label_drawings_and_never_fabricate_photos(self):
        sc = art.scene_visual('technical_illustration', {'kind': 'screw_crown'}, 'tk-bone', 5)
        self.assertTrue(any(e.get('text') == art.DRAWING_NOTE for e in sc['elements']))
        self.assertTrue(all(e.get('type') != 'watch' for e in sc['elements']))
        miss = art.missing_assets('product_macro', {'asset': 'gleitze_oyster_photo', 'desc': 'x'}, Path(self.tmp.name) / 'none')
        self.assertEqual(miss, ['gleitze_oyster_photo'])
        m = {s['id']: s['level'] for s in art.support_matrix(self.S.profile('timekeeper'))}
        self.assertEqual(m['ai_illustration'], 'paid tool')
        self.assertEqual(m['product_macro'], 'supported (needs real material)')

    def test_finding_accept_creates_task_dismiss_keeps_history(self):
        f = {'id': 'f1', 'code': 'MISSING_ASSET', 'severity': 'major', 'scene': 'l11', 't': 3.0, 'recommendation': 'add the photo',
             'perspective': 'historical_product', 'detail': 'x', 'evidence': None}
        self.S.act(self.pid, 'review', {'id': 'rv1', 'render': 'r1', 'label': 'draft', 'findings': [f, {**f, 'id': 'f2'}], 'counts': {}}, 'reviewer')
        self.S.act(self.pid, 'finding_decision', {'finding': 'f1', 'decision': 'accepted'})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'finding_decision', {'finding': 'f2', 'decision': 'dismissed'})
        self.S.act(self.pid, 'finding_decision', {'finding': 'f2', 'decision': 'dismissed', 'note': 'fine for a draft'})
        st = self.S.state(self.pid)
        self.assertEqual([t['id'] for t in st['fix_tasks']], ['fix-f1'])
        self.assertEqual(st['review']['findings']['f2']['decision_note'], 'fine for a draft')


class TestFinalGate(Env):
    def test_plan_blockers_and_refusals_with_no_paid_call(self):
        self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})
        v = self.approved_v2()
        g = gate.plan(self.S, self.pid)
        lines = self.S.read_json(self.pid, self.S.state(self.pid)['scripts'][-1]['file'])['lines']
        self.assertEqual([i['provider_input'] for i in g['items']], [l['text'] for l in lines])   # names not yet approved
        self.assertEqual(g['chars_total'], sum(len(l['text']) for l in lines))
        text = ' | '.join(g['blockers'])
        for k in ('royal-oak', 'disabled', 'budget', 'proposed'):
            self.assertIn(k, text)
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'gate_authorize', {'plan': g['hash'], 'confirm_text': str(g['chars_total'])})
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'final_generate', {})
        code, r = api.handle(self.tmp.name, {'project': self.pid, 'action': 'final_generate'})
        self.assertEqual(code, 422)

    def test_gateway_rules_on_a_studio_plan_with_a_mock_provider(self):
        """MOCK ONLY: proves the gate's rules, not that ElevenLabs works."""
        self.S.act(self.pid, 'set_voice', {'voice': 'abdullah'})
        self.approved_v2()
        plan = gate.plan(self.S, self.pid)['plan']
        tr = MockTransport()
        L = Ledger(Path(self.tmp.name) / 'ledger-mock.sqlite')
        store = TakeStore(self.S.pdir(self.pid) / 'final-takes')
        off = PaidGateway(L, store, {'elevenlabs': ElevenLabsProvider(tr)})          # environment says disabled
        aid = off.approve(plan, 'owner')
        with self.assertRaises(PaidCallRefused):
            off.run(plan, aid)
        on = PaidGateway(L, store, {'elevenlabs': ElevenLabsProvider(tr)}, enabled=True)
        with self.assertRaises(PaidCallRefused):                                      # no budget
            on.run(plan, aid)
        L.set_budget(self.pid, 'elevenlabs', plan['chars_total'] - 1)
        with self.assertRaises(PaidCallRefused):                                      # budget too small
            on.run(plan, aid)
        L.set_budget(self.pid, 'elevenlabs', plan['chars_total'])
        tampered = {**plan, 'items': plan['items'][:-1]}
        with self.assertRaises(PaidCallRefused):
            on.run(tampered, aid)
        rep = on.run(plan, aid)
        self.assertEqual(len(tr.calls), 13); self.assertEqual(rep['units'], plan['chars_total'])
        with self.assertRaises(PaidCallRefused):                                      # single use
            on.run(plan, aid)
        self.assertEqual(len(tr.calls), 13)

    def test_studio_code_has_no_path_to_paid_providers(self):
        banned = ('gateway', 'urllib', 'http.client', 'requests', 'socket', 'elevenlabs')
        for f in (ROOT / 'director/studio').glob('*.py'):
            for node in ast.walk(ast.parse(f.read_text(encoding='utf-8'))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                        [node.module or ''] + [a.name for a in node.names] if isinstance(node, ast.ImportFrom) else []
                for n in names:
                    self.assertFalse(any(b in n for b in banned), f'{f.name} imports {n}')
        page = (ROOT / 'director/studio/studio.html').read_text(encoding='utf-8')
        self.assertNotIn('elevenlabs.io', page)


if __name__ == '__main__':
    unittest.main()
