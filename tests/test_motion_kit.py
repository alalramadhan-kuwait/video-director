"""The motion kit from video-ad-editor (vendor/motion-kit): vendored as copied, wired into the engine, and the number
templates draw what they are given, in the safe band, the same way every time."""
from tests import _guard  # noqa: F401
import hashlib, re, shutil, tempfile, unittest
from pathlib import Path

from director.studio import art, engine

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'vendor/motion-kit'
NUMBERS = ('stat_counter', 'part_of_whole', 'trend_chart', 'compare_bars')


def _kits(sc):
    return [e for e in sc['elements'] if e['type'] == 'kit']


class TestVendored(unittest.TestCase):
    def test_the_kit_is_the_copied_file_with_its_licence(self):
        want = re.search(r'\| motion-kit\.js \|[^|]+\| ([0-9a-f]{64}) \|', (KIT / 'PROVENANCE.md').read_text(encoding='utf-8')).group(1)
        self.assertEqual(hashlib.sha256((KIT / 'motion-kit.js').read_bytes()).hexdigest(), want)
        self.assertIn('MIT License', (KIT / 'LICENSE').read_text(encoding='utf-8'))

    def test_the_stage_loads_the_kit_after_the_engine(self):
        html = (ROOT / 'vendor/paper-story/engine/stage.html').read_text(encoding='utf-8')
        order = [html.index(s) for s in ('paper.js', 'motion-kit/motion-kit.js', 'motion-kit/kit-element.js')]
        self.assertEqual(order, sorted(order))


class TestNumberTemplates(unittest.TestCase):
    def setUp(self):
        self.cat = {t['id']: t for t in art.catalogue()}
        self.fns = set(re.findall(r'MK\.(\w+) = function', (KIT / 'motion-kit.js').read_text(encoding='utf-8')))

    def test_each_calls_real_kit_components_and_shows_its_source(self):
        for tid in NUMBERS:
            sc = art.scene_visual(tid, self.cat[tid]['example'], 'tk-bone', 4.5)
            kits = _kits(sc)
            self.assertEqual(len(kits), 1, tid)
            self.assertLessEqual({d['fn'] for d in kits[0]['draw']}, self.fns, tid)
            self.assertTrue(any(e.get('text') == self.cat[tid]['example']['source'] for e in sc['elements']), tid)
            self.assertTrue(sc.get('sfx'), tid)

    def test_the_number_lands_when_it_is_said(self):
        sc = art.scene_visual('stat_counter', {'value': 1936, 'land': 2.4, 'dur': 1.5}, 'tk-ink', 4.5)
        od = _kits(sc)[0]['draw'][0]
        self.assertAlmostEqual(od['s'] + od['dur'], 2.4)
        self.assertIn({'at': 2.4, 'name': 'click', 'gain': -11}, sc['sfx'])
        hot = _kits(art.scene_visual('part_of_whole', {'total': 50, 'hot': 3, 'land': 2.2}, 'tk-bone', 4.5))[0]['draw'][0]
        self.assertEqual((hot['hotAt'], hot['total'], hot['hot']), (2.2, 50, 3))

    def test_an_arabic_unit_reads_after_the_number(self):
        od = _kits(art.scene_visual('stat_counter', {'value': 200, 'suffix': ' م'}, 'tk-bone', 4))[0]['draw'][0]
        self.assertEqual((od['prefix'].strip(), od['suffix']), ('م', ''))
        od = _kits(art.scene_visual('stat_counter', {'value': 37, 'suffix': ' mm'}, 'tk-bone', 4))[0]['draw'][0]
        self.assertEqual(od['suffix'], ' mm')

    def test_a_trend_keeps_the_shape_of_its_values(self):
        pts = _kits(art.scene_visual('trend_chart', {'values': [10, 5, 20]}, 'tk-bone', 4))[0]['draw'][0]['points']
        self.assertEqual(pts[0], .46); self.assertEqual(pts[24], .23); self.assertEqual(pts[-1], .92)
        self.assertTrue(all(0 <= v <= 1 for v in pts))

    def test_kit_boxes_stay_in_the_safe_band(self):
        for tid in NUMBERS:
            for d in _kits(art.scene_visual(tid, self.cat[tid]['example'], 'tk-bone', 4.5))[0]['draw']:
                b = d.get('box') or {'x': d['cx'] - 300, 'y': d['cy'] - d['size'], 'w': 600, 'h': d['size']}
                self.assertGreaterEqual(b['y'], 570, tid); self.assertLessEqual(b['y'] + b['h'], 1470, tid)
                self.assertGreaterEqual(b['x'], 72, tid); self.assertLessEqual(b['x'] + b['w'], 950, tid)


HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()


@unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
class TestKitRenders(unittest.TestCase):
    def _sb(self, sc):
        return {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': [sc]}

    def test_the_counter_is_drawn_and_every_render_of_a_frame_is_the_same(self):
        from PIL import Image
        sc = art.scene_visual('stat_counter', {'value': 200, 'land': 1.0, 'dur': .8}, 'tk-bone', 3.0)
        sc['dur'] = 3.0
        with tempfile.TemporaryDirectory() as d:
            a = engine.stills(self._sb(sc), Path(d) / 'a', [0.05, 2.0], scale=0.5)
            b = engine.stills(self._sb(sc), Path(d) / 'b', [2.0], scale=0.5)
            self.assertEqual(a[1].read_bytes(), b[0].read_bytes())
            dark = lambda p: sum(1 for px in Image.open(p).convert('L').crop((90, 280, 270, 360)).getdata() if px < 80)
            self.assertEqual(dark(a[0]), 0)                       # before the digits start: nothing there
            self.assertGreater(dark(a[1]), 400)                   # after it lands: the number, in ink

    def test_an_unknown_component_fails_the_render(self):
        sc = art.scene_visual('kinetic_type', {'lines': [{'text': 'اختبار'}]}, 'tk-bone', 2.0)
        sc['dur'] = 2.0
        sc['elements'].append({'type': 'kit', 'draw': [{'fn': 'noSuchThing', 's': 0}]})
        with tempfile.TemporaryDirectory() as d, self.assertRaises(RuntimeError) as e:
            engine.stills(self._sb(sc), Path(d), [1.0], scale=0.5)
        self.assertIn('kit-element.js', str(e.exception))           # refused by the kit element, before any frame


if __name__ == '__main__':
    unittest.main()
