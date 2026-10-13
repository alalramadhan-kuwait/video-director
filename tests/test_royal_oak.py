"""Acceptance test on real, already-approved metadata and the 30 recovered takes (no generation, no network)."""
from tests import _guard  # noqa: F401
import json, os, tempfile, unittest
from director import importers
from director.library import Library
from director.ledger import Ledger
from director.voice.takes import TakeStore
from director.voice.plan import build_plan
from director.voice.imports import import_eleven_manifest
from director.voice.gateway import PaidGateway, ElevenLabsProvider
from director import profiles
from tests.fixtures import RO, RO_AUDIO, PROFILES, have_ro


@unittest.skipUnless(have_ro, 'Royal Oak clone or recovered audio not present')
class TestRoyalOak(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = TakeStore(os.path.join(cls.tmp.name, 'store'))
        cls.keys = import_eleven_manifest(RO / 'voice-abdullah/clips.json', RO_AUDIO, cls.store, 'royal-oak')
        cls.lib = Library(importers.keep_arabic_overrides(RO / 'script-msa3.json') + importers.habibi_pron(RO / 'tts_habibi.py'))
        cls.man = json.loads((RO / 'voice-abdullah/clips.json').read_text(encoding='utf-8'))
        cls.lines = [{'id': k, 'text': v['text']} for k, v in cls.man.items()]
        tk = profiles.load(PROFILES / 'timekeeper-luxury-doc.yaml')
        cls.voice = profiles.voice_for(tk, 'abdullah', 'royal-oak')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_import_keeps_audio_identical(self):
        self.assertEqual(len(self.keys), 30)
        for k in self.keys:
            self.assertTrue(self.store.verify(k))
            self.assertEqual(self.store.status(k), 'approved')

    def test_library_reproduces_every_approved_input(self):
        for ln in self.lines:
            out, _ = self.lib.prepare(ln['text'], 'elevenlabs', line=ln['id'], accept=('imported', 'approved'))
            self.assertEqual(out, self.man[ln['id']]['spoken'], ln['id'])

    def test_unchanged_script_bills_nothing(self):
        p = build_plan('royal-oak', self.lines, self.voice, self.lib, self.store, accept=('imported', 'approved'))
        self.assertEqual(p['totals'], {'reuse': 30, 'review': 0, 'blocked': 0, 'new': 0})
        self.assertEqual(p['chars_total'], 0)

    def test_one_changed_line_bills_exactly_one(self):
        lines = [dict(l) for l in self.lines]
        lines[5]['text'] = lines[5]['text'].replace('…', '،', 1) if '…' in lines[5]['text'] else lines[5]['text'] + ' '
        p = build_plan('royal-oak', lines, self.voice, self.lib, self.store, accept=('imported', 'approved'))
        self.assertEqual(p['totals']['new'], 1)
        self.assertEqual(p['totals']['reuse'], 29)
        new = [i for i in p['items'] if i['action'] == 'new'][0]
        self.assertEqual(new['line'], lines[5]['id'])
        self.assertEqual(p['chars_total'], len(new['provider_input']))

    def test_gateway_would_send_nothing_for_unchanged_script(self):
        calls = []
        tmp = tempfile.TemporaryDirectory()
        led = Ledger(os.path.join(tmp.name, 'l.sqlite')); led.set_budget('royal-oak', 'elevenlabs', 1000)
        gw = PaidGateway(led, self.store, {'elevenlabs': ElevenLabsProvider(lambda r: calls.append(r))}, enabled=True)
        p = build_plan('royal-oak', self.lines, self.voice, self.lib, self.store, accept=('imported', 'approved'))
        rep = gw.run(p, gw.approve(p, by='owner'))
        self.assertEqual((calls, rep['units']), ([], 0))
        tmp.cleanup()

    def test_article_findings_on_the_approved_script(self):
        """Lines where an «الـ» word went to the voice in Latin. Reported for listening, not regenerated."""
        found = {}
        for ln in self.lines:
            _, fs = self.lib.prepare(ln['text'], 'elevenlabs', line=ln['id'], accept=('imported', 'approved'))
            for f in fs:
                if f.code == 'ARTICLE_DROPPED':
                    found.setdefault(ln['id'], []).append(f.entry)
        self.assertNotIn('p2-h', found)                     # the _arabic override protects the hook line
        print('\nARTICLE_DROPPED in approved Royal Oak lines:', json.dumps(found, ensure_ascii=False))


if __name__ == '__main__':
    unittest.main()
