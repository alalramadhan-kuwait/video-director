"""Voice review page on the real approved Royal Oak takes (read-only) + ingest of the owner's answers.
Needs the local word timings in var/asr/royal-oak (python -m director.review.asr); no network, no generation."""
from tests import _guard  # noqa: F401
import hashlib, json, os, tempfile, unittest
from pathlib import Path
from director import importers, profiles
from director.library import Library
from director.voice.takes import TakeStore
from director.voice.imports import import_eleven_manifest
from director.voice.gateway import PaidGateway, ElevenLabsProvider, PaidCallRefused
from director.ledger import Ledger
from director.review.voice_page import build
from director.review.voice_ingest import ingest
from tests.fixtures import RO, RO_AUDIO, PROFILES, S, have_ro

ROOT = Path(__file__).resolve().parent.parent
ASR = ROOT / 'var/asr/royal-oak'
QUEUE = {'p2-1', 'p2-2', 'p2-4', 'p2-6', 'p2-q', 'p2-8', 'p3-e', 'p3-h'}


def tree_hash(d):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).glob('*.mp3'))}


@unittest.skipUnless(have_ro and ASR.exists() and len(list(ASR.glob('*.json'))) == 30, 'Royal Oak takes or word timings missing')
class TestVoiceReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(); t = Path(cls.tmp.name)
        cls.before = tree_hash(RO_AUDIO)
        cls.store = TakeStore(t / 'store')
        cls.approved = import_eleven_manifest(RO / 'voice-abdullah/clips.json', RO_AUDIO, cls.store, 'royal-oak')
        cls.lib = Library(importers.keep_arabic_overrides(RO / 'script-msa3.json') + importers.habibi_pron(RO / 'tts_habibi.py'))
        cls.voice = profiles.voice_for(profiles.load(PROFILES / 'timekeeper-luxury-doc.yaml'), 'abdullah', 'royal-oak')
        hist = json.loads((S / 'phase05/royal-oak/history_abdullah.json').read_text(encoding='utf-8'))['history']
        cls.data, cls.files = build(project='royal-oak', manifest=RO / 'voice-abdullah/clips.json', audio_dir=RO_AUDIO,
                                    asr_dir=ASR, library=cls.lib, store=cls.store, voice=cls.voice, out_dir=t / 'page',
                                    history=hist, mock_dir=t / 'mock')
        cls.L = {l['id']: l for l in cls.data['lines']}
        cls.page = t / 'page'

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_queue_is_exactly_the_eight_common_noun_lines(self):
        self.assertEqual(set(self.data['queue']), QUEUE)
        self.assertNotIn('p2-h', self.data['queue'])                   # protected by its _arabic override

    def test_every_queue_question_points_at_the_written_word(self):
        for lid in QUEUE:
            l = self.L[lid]; words = l['takes'][0]['words']
            for q in l['questions']:
                self.assertTrue(q['words'], (lid, q['written']))
                said = ' '.join(words[i]['w'] for i in q['words'])
                for part in q['written'].split():
                    self.assertIn(part, said, (lid, q['written'], said))
                s, e = words[q['words'][0]]['s'], words[q['words'][-1]]['e']
                self.assertTrue(0 <= s < e <= l['takes'][0]['duration'] + 0.1, (lid, s, e))

    def test_repeated_word_gets_two_targets(self):
        qs = [q for q in self.L['p2-6']['questions'] if q['entry'] == 'tk-steel']
        self.assertEqual(len(qs), 2)
        self.assertNotEqual(qs[0]['words'], qs[1]['words'])

    def test_exact_input_and_costs(self):
        self.assertEqual(self.data['chars_total'], 0)
        man = json.loads((RO / 'voice-abdullah/clips.json').read_text(encoding='utf-8'))
        for lid, l in self.L.items():
            self.assertEqual(l['provider_input'], man[lid]['spoken'])            # what was really sent
            self.assertEqual((l['plan']['action'], l['plan']['chars']), ('reuse', 0))
        ka = self.L['p2-1']['corrections']['keep_arabic']
        self.assertIn('الستيل', ka['provider_input']); self.assertNotIn('Steel', ka['provider_input'])
        self.assertEqual((ka['action'], ka['chars']), ('new', len(ka['provider_input'])))

    def test_mock_takes_are_labelled_and_separate(self):
        for lid in QUEUE:
            kinds = [t['kind'] for t in self.L[lid]['takes']]
            self.assertEqual(kinds, ['approved', 'mock'])
            mock = self.L[lid]['takes'][1]
            self.assertEqual(self.store.get(mock['id'])['request']['provider'], 'mock')
            self.assertEqual(self.store.events(mock['id'])[0]['status'], 'candidate')   # created as a candidate
            self.assertNotIn(mock['id'], self.approved)

    def test_page_is_self_contained_and_small(self):
        html = (self.page / 'index.html').read_text(encoding='utf-8')
        self.assertLess(len(html.encode()), 2_000_000)
        self.assertNotIn('api.elevenlabs', html); self.assertNotIn('xi-api-key', html)
        total = sum((self.page / f).stat().st_size for f in self.files) + len(html.encode())
        self.assertLess(total, 64_000_000)
        for f in self.files:
            self.assertTrue((self.page / f).exists(), f)

    def test_originals_untouched(self):
        self.assertEqual(tree_hash(RO_AUDIO), self.before)
        for k in self.approved:
            self.assertEqual(self.store.status(k), 'approved'); self.assertTrue(self.store.verify(k))

    def test_ingest_turns_answers_into_proposals_not_changes(self):
        p21 = self.L['p2-1']; q = p21['questions'][0]; take = p21['takes'][0]['id']; mock = p21['takes'][1]['id']
        rows = {'listening': {q['key']: {'line': 'p2-1', 'entry': q['entry'], 'written': q['written'], 'sent': q['sent'],
                                         'heard': 'article_missing', 'take': take, 'take_kind': 'approved'}},
                'verdicts': {f'p2-1~{take}': {'line': 'p2-1', 'take': take, 'take_kind': 'approved', 'verdict': 'reject', 'reason': 'no al'},
                             f'p2-1~{mock}': {'line': 'p2-1', 'take': mock, 'take_kind': 'mock', 'verdict': 'reject'}},
                'corrections': {'p2-1': {'line': 'p2-1', 'option': 'keep_arabic'},
                                'p3-h': {'line': 'p3-h', 'option': 'leave'}},
                'marks': {}}
        with tempfile.TemporaryDirectory() as d:
            r = ingest(rows, self.data, self.lib, self.store, self.voice, d)
            self.assertEqual(self.store.status(take), 'approved')                     # approved stays approved
            self.assertEqual(self.store.status(mock), 'rejected')                     # mock follows the verdict
            dec = [json.loads(x) for x in open(os.path.join(d, 'decisions.jsonl'), encoding='utf-8')]
            self.assertIn('replace_requested', [x.get('decision') for x in dec])
            self.assertEqual(r['proposals'], ['prop-p2-1-tk-steel'])
            props = Library.load(os.path.join(d, 'proposals.yaml'))
            self.assertEqual([e.status for e in props.entries], ['proposed'])
            self.assertEqual(r['what_if']['lines'], ['p2-1'])
            self.assertEqual(r['what_if']['chars_total'], p21['corrections']['keep_arabic']['chars'])
            # the what-if plan cannot be run without an approval for that exact plan, and it is disabled anyway
            plan = json.loads(open(os.path.join(d, 'what_if_plan.json'), encoding='utf-8').read())
            calls = []
            gw = PaidGateway(Ledger(os.path.join(d, 'l.sqlite')), self.store,
                             {'elevenlabs': ElevenLabsProvider(lambda req: calls.append(req))})
            with self.assertRaises(PaidCallRefused):
                gw.run(plan, 'ap_none')
            self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
