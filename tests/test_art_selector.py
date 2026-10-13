from tests import _guard  # noqa: F401
import json, os, tempfile, unittest
import yaml
from director.art.selector import load_registry, recommend, record_choice
from director import profiles
from tests.fixtures import PROFILES
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = load_registry(ROOT / 'art/techniques.yaml')
TK = profiles.load(PROFILES / 'timekeeper-luxury-doc.yaml')
DH = profiles.load(PROFILES / 'diabetes-history-sci.yaml')
TKB = {s['id']: s for s in yaml.safe_load((ROOT / 'art/mock/royal-oak-beats.yaml').read_text())['scenes']}
DHB = {s['id']: s for s in yaml.safe_load((ROOT / 'art/mock/diabetes-ep7-beats.yaml').read_text())['scenes']}
ids = lambda r: [o['technique'] for o in r['options']]


class TestSelector(unittest.TestCase):
    def test_registry_is_complete(self):
        for t in REG.values():
            for k in ('status', 'support', 'cost', 'accuracy', 'risks', 'good_for'):
                self.assertIn(k, t, t['id'])
        self.assertTrue({'paper_cut', 'archival_collage', 'scientific_diagram', 'verified_3d', 'live_footage'} <= set(REG))

    def test_every_mock_scene_gets_three_options(self):
        for prof, beats in ((TK, TKB), (DH, DHB)):
            for s in beats.values():
                r = recommend(s, prof, REG)
                if s['beat'] == 'person_real':
                    # a real person with a photo has few honest options; the selector must say so rather than pad the list
                    self.assertGreaterEqual(len(r['options']), 2, s['id'])
                else:
                    self.assertTrue(r['enough_options'], (s['id'], ids(r)))

    def test_zero_budget_never_offers_paid_techniques(self):
        for prof, beats in ((TK, TKB), (DH, DHB)):
            for s in beats.values():
                self.assertNotIn('ai_illustration', ids(recommend(s, prof, REG)))

    def test_no_invented_faces(self):
        r = recommend(TKB['p2-0b'], TK, REG)
        self.assertEqual(ids(r)[0], 'neutral_placeholder')
        self.assertNotIn('character_animation', ids(r))
        self.assertTrue(any(e['technique'] == 'parallax_25d' and 'invent' in e['reason'] for e in r['excluded']) or
                        'parallax_25d' not in ids(r))

    def test_real_products_are_never_ai_even_with_budget(self):
        s = {**TKB['p2-4'], 'max_cost': 10, 'assets': TKB['p2-4']['assets'] + ['reference_images']}
        r = recommend(s, TK, REG)
        self.assertNotIn('ai_illustration', ids(r))
        self.assertTrue(any(e['technique'] == 'ai_illustration' for e in r['excluded']))

    def test_profiles_drive_different_choices(self):
        self.assertEqual(ids(recommend(TKB['p2-4'], TK, REG))[0], 'archival_collage')
        self.assertEqual(ids(recommend(DHB['b3'], DH, REG))[0], 'scientific_diagram')
        # the same mechanism beat leads with different techniques in each identity
        same = {'id': 'x', 'beat': 'mechanism', 'accuracy': 'high', 'assets': ['technical_sheet', 'source', 'data']}
        self.assertNotEqual(ids(recommend(same, TK, REG))[0], ids(recommend(same, DH, REG))[0])

    def test_missing_assets_are_explained(self):
        r = recommend({'id': 'y', 'beat': 'product', 'accuracy': 'high', 'assets': []}, TK, REG)
        top = r['options'][0]
        self.assertTrue(any('missing assets' in w for w in top['warnings']) or top['technique'] != 'product_macro')

    def test_choices_are_recorded_per_project(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, 'decisions.jsonl')
            record_choice(log, 'royal-oak', 'p2-4', 'product_macro', [{'technique': 'archival_collage', 'why': 'too busy'}], reason='owner preference')
            row = json.loads(open(log).read())
            self.assertEqual((row['project'], row['chosen']), ('royal-oak', 'product_macro'))


if __name__ == '__main__':
    unittest.main()
