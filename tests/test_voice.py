from tests import _guard  # noqa: F401
import json, os, stat, tempfile, time, unittest
from director.library import Library, Entry
from director.ledger import Ledger
from director.voice.takes import TakeStore, TakeStoreError, take_key
from director.voice.plan import build_plan
from director.voice.gateway import PaidGateway, ElevenLabsProvider, PaidCallRefused

VOICE = {'provider': 'elevenlabs', 'voice_id': 'VOICE_X', 'model': 'eleven_multilingual_v2',
         'settings': {'stability': 0.5, 'similarity_boost': 0.75, 'style': 0, 'use_speaker_boost': True, 'speed': 1.0},
         'seed': 1234, 'output_format': 'mp3_44100_128'}
LIB = Library([Entry(id='steel', scope='brand:timekeeper', surface='ستيل', status='approved',
                     providers={'elevenlabs': {'mode': 'keep_arabic'}})])
LINES = [{'id': 'l1', 'text': 'ساعةٌ من الستيل'}, {'id': 'l2', 'text': 'بسعرٍ أعلى من الذهب'}, {'id': 'l3', 'text': 'كيف؟'}]


class MockTransport:
    """Records every request; returns fake audio. `fail_on` makes one call raise."""
    def __init__(self, fail_on=None):
        self.calls, self.fail_on = [], fail_on
    def __call__(self, request):
        self.calls.append(request)
        if self.fail_on and self.fail_on in request['json']['text']:
            raise IOError('mock provider error')
        return b'ID3fake-audio:' + request['json']['text'].encode()


class Env(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = TakeStore(os.path.join(self.tmp.name, 'store'))
        self.ledger = Ledger(os.path.join(self.tmp.name, 'ledger.sqlite'))
        self.transport = MockTransport()
        self.gw = PaidGateway(self.ledger, self.store, {'elevenlabs': ElevenLabsProvider(self.transport)}, enabled=True)
    def tearDown(self):
        self.tmp.cleanup()
    def plan(self, lines=LINES):
        return build_plan('demo', lines, VOICE, LIB, self.store)


class TestTakeStore(Env):
    def req(self, text='نص'):
        return {**{k: VOICE[k] for k in VOICE}, 'provider_input': text}

    def test_put_is_write_once_and_read_only(self):
        k = self.store.put(self.req(), b'AAA')
        self.assertEqual(self.store.put(self.req(), b'AAA'), k)                       # idempotent
        with self.assertRaises(TakeStoreError):
            self.store.put(self.req(), b'BBB')                                        # never overwritten
        p = self.store.audio_path(k)
        self.assertFalse(os.stat(p).st_mode & stat.S_IWUSR)
        self.assertTrue(self.store.verify(k))

    def test_key_ignores_metadata_but_not_request(self):
        a = take_key(self.req())
        self.assertEqual(a, take_key({**self.req(), 'library_version': 'zzz'}))       # extra fields don't matter
        self.assertNotEqual(a, take_key({**self.req(), 'seed': 1}))
        self.assertNotEqual(a, take_key(self.req('نصّ')))

    def test_status_is_append_only_and_final(self):
        k = self.store.put(self.req(), b'A')
        self.store.set_status(k, 'approved', by='owner')
        with self.assertRaises(TakeStoreError):
            self.store.set_status(k, 'rejected', by='someone')                        # approved is final
        self.assertEqual([e['status'] for e in self.store.events(k)], ['candidate', 'approved'])


class TestPlan(Env):
    def test_new_reuse_review_blocked(self):
        p = self.plan()
        self.assertEqual(p['totals'], {'reuse': 0, 'review': 0, 'blocked': 0, 'new': 3})
        self.assertEqual(p['chars_total'], sum(len(l['text']) for l in LINES))
        it = {i['line']: i for i in p['items']}
        self.store.put(it['l1']['request'], b'1', status='approved', by='owner')
        self.store.put(it['l2']['request'], b'2', status='candidate', by='gateway')
        k3 = self.store.put(it['l3']['request'], b'3', status='candidate', by='gateway')
        self.store.set_status(k3, 'rejected', by='owner')
        p2 = self.plan()
        self.assertEqual(p2['totals'], {'reuse': 1, 'review': 1, 'blocked': 1, 'new': 0})
        self.assertEqual(p2['chars_total'], 0)

    def test_changing_one_line_bills_only_that_line(self):
        p = self.plan()
        for i in p['items']:
            self.store.put(i['request'], i['line'].encode(), status='approved', by='owner')
        changed = [dict(l) for l in LINES]
        changed[1]['text'] = 'بسعرٍ أعلى من الذهب الأبيض'
        p2 = self.plan(changed)
        self.assertEqual(p2['totals']['new'], 1)
        self.assertEqual([i['line'] for i in p2['items'] if i['action'] == 'new'], ['l2'])
        self.assertEqual(p2['chars_total'], len(changed[1]['text']))


class TestGateway(Env):
    def approved_run(self, plan=None, budget=10_000):
        plan = plan or self.plan()
        self.ledger.set_budget('demo', 'elevenlabs', budget)
        return plan, self.gw.approve(plan, by='owner')

    def test_disabled_by_default(self):
        gw = PaidGateway(self.ledger, self.store, {'elevenlabs': ElevenLabsProvider(self.transport)})  # no enabled=
        os.environ.pop('VIDEO_DIRECTOR_PAID_ENABLED', None)
        plan, ap = self.approved_run()
        with self.assertRaisesRegex(PaidCallRefused, 'disabled'):
            gw.run(plan, ap)
        self.assertEqual(self.transport.calls, [])

    def test_provider_refuses_direct_calls(self):
        with self.assertRaises(PaidCallRefused):
            ElevenLabsProvider(self.transport).synthesize({**VOICE, 'provider_input': 'x'})
        self.assertEqual(self.transport.calls, [])

    def test_happy_path_generates_only_new_items_once(self):
        plan, ap = self.approved_run()
        rep = self.gw.run(plan, ap)
        self.assertEqual(len(self.transport.calls), 3)
        self.assertEqual(rep['units'], plan['chars_total'])
        self.assertEqual(self.ledger.spent('demo', 'elevenlabs'), plan['chars_total'])
        for g in rep['generated']:
            self.assertEqual(self.store.status(g['take']), 'candidate')               # never auto-approved
        self.assertEqual(self.transport.calls[0]['url'], 'https://api.elevenlabs.io/v1/text-to-speech/VOICE_X')
        self.assertEqual(self.transport.calls[0]['json']['seed'], 1234)

    def test_approval_is_single_use(self):
        plan, ap = self.approved_run()
        self.gw.run(plan, ap)
        with self.assertRaisesRegex(PaidCallRefused, 'already used'):
            self.gw.run(plan, ap)
        self.assertEqual(len(self.transport.calls), 3)

    def test_approval_bound_to_plan(self):
        plan, ap = self.approved_run()
        other = self.plan(LINES[:1])
        with self.assertRaisesRegex(PaidCallRefused, 'different plan'):
            self.gw.run(other, ap)
        tampered = json.loads(json.dumps(plan)); tampered['items'][0]['provider_input'] = 'شيء آخر'
        with self.assertRaisesRegex(PaidCallRefused, 'does not match its hash'):
            self.gw.run(tampered, ap)
        self.assertEqual(self.transport.calls, [])

    def test_expired_approval(self):
        plan = self.plan(); self.ledger.set_budget('demo', 'elevenlabs', 10_000)
        ap = self.ledger.create_approval(plan['hash'], 'demo', 'elevenlabs', plan['chars_total'], 'owner', ttl_s=-1)
        with self.assertRaisesRegex(PaidCallRefused, 'expired'):
            self.gw.run(plan, ap)

    def test_budget_and_missing_budget(self):
        plan = self.plan()
        ap = self.gw.approve(plan, by='owner')
        with self.assertRaisesRegex(PaidCallRefused, 'no budget'):
            self.gw.run(plan, ap)
        self.ledger.set_budget('demo', 'elevenlabs', 5)
        with self.assertRaisesRegex(PaidCallRefused, 'budget too small'):
            self.gw.run(plan, ap)
        self.assertEqual(self.transport.calls, [])

    def test_failure_stops_without_retry(self):
        self.transport.fail_on = 'بسعرٍ'
        plan, ap = self.approved_run()
        rep = self.gw.run(plan, ap)
        self.assertEqual(len(self.transport.calls), 2)                                # l1 ok, l2 failed once, l3 never tried
        self.assertEqual(rep['failed']['line'], 'l2')
        self.assertEqual(self.ledger.spent('demo', 'elevenlabs'), len(LINES[0]['text']))
        with self.assertRaisesRegex(PaidCallRefused, 'already used'):
            self.gw.run(plan, ap)                                                     # a retry needs a new approval

    def test_reused_lines_are_never_sent(self):
        p = self.plan()
        for i in p['items'][:2]:
            self.store.put(i['request'], b'x', status='approved', by='owner')
        plan, ap = self.approved_run(self.plan())
        self.gw.run(plan, ap)
        self.assertEqual([c['json']['text'] for c in self.transport.calls], [LINES[2]['text']])

    def test_audit_trail(self):
        plan, ap = self.approved_run()
        self.gw.run(plan, ap)
        actions = [r['action'] for r in self.ledger.audit_rows()]
        self.assertEqual(actions, ['set_budget', 'approve_plan', 'paid_run_start', 'paid_run_end'])


if __name__ == '__main__':
    unittest.main()
