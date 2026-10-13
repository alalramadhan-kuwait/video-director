"""Creative directions: no invented colours or fonts, engine facts from the registry, profiles never written."""
from tests import _guard  # noqa: F401
import copy, hashlib, unittest
from pathlib import Path
import yaml
from director.art import directions as DR
from director.art.selector import load_registry
from tests.fixtures import S

ROOT = Path(__file__).resolve().parent.parent
DOC = yaml.safe_load((ROOT / 'profiles/directions.yaml').read_text(encoding='utf-8'))
PATHS = DR.source_paths(S)
have_sources = all(p is not None and Path(p).exists() for k, p in PATHS.items())


def first(doc, did):
    return next(d for p in doc['projects'].values() for d in p['directions'] if d['id'] == did)


@unittest.skipUnless(have_sources, 'approved source files not present')
class TestDirections(unittest.TestCase):
    def test_every_value_is_backed_by_its_source(self):
        self.assertEqual(DR.check_sources(DOC, PATHS), [])

    def test_invented_colour_is_refused(self):
        doc = copy.deepcopy(DOC); first(doc, 'tk-editorial')['palette']['values']['gold'] = '#C9A35B'
        self.assertTrue(any('#C9A35B' in e for e in DR.check_sources(doc, PATHS)))

    def test_invented_font_is_refused(self):
        doc = copy.deepcopy(DOC); first(doc, 'tk-paper')['fonts']['values']['body'] = 'Playfair Display'
        self.assertTrue(any('Playfair' in e for e in DR.check_sources(doc, PATHS)))

    def test_values_need_a_source_and_gaps_must_say_so(self):
        doc = copy.deepcopy(DOC)
        first(doc, 'dh-papercut')['palette']['source'] = None
        first(doc, 'dh-archival')['palette'].pop('missing')
        first(doc, 'tk-editorial')['palette']['accent'] = '#111111'
        errs = DR.check_sources(doc, PATHS)
        self.assertTrue(any('dh-papercut/palette: values without a source' in e for e in errs))
        self.assertTrue(any('dh-archival/palette: unassigned without saying so' in e for e in errs))
        self.assertTrue(any('tk-editorial: accent' in e for e in errs))

    def test_engine_facts_come_from_the_registry(self):
        reg = load_registry(ROOT / 'art/techniques.yaml')
        data = DR.build_data(DOC, reg)
        for proj in data['projects'].values():
            self.assertEqual(len(proj['directions']), 3)                    # several directions per project
            self.assertEqual(proj['profile_status'], 'draft')
            for d in proj['directions']:
                for t in d['techniques']:
                    self.assertEqual((t['status'], t['cost']), (reg[t['id']]['status'], reg[t['id']]['cost']))
                self.assertIn('no paid image or video generation', d['cost']['images'])
                for k in ('visual_style', 'suitable_scenes', 'required_assets', 'limitations', 'accuracy_risks'):
                    self.assertTrue(d[k], (d['id'], k))

    def test_building_the_page_never_writes_a_profile(self):
        import tempfile
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'profiles').glob('*.yaml')}
        with tempfile.TemporaryDirectory() as d:
            DR.build(d, S, ROOT / 'var/review/ep7-final',
                     Path('/home/user/majedphotos/video-ad-editor/video-ad-editor/motion/fonts/Cairo-VF.ttf'))
            self.assertTrue((Path(d) / 'index.html').exists())
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'profiles').glob('*.yaml')}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
