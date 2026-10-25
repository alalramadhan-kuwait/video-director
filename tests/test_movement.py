"""The mechanical watch movement (vendor/studio-ext/movement3d.js): a catalogued, labelled template that renders in
3D, runs from the scene time alone, and lifts apart with its names."""
from tests import _guard  # noqa: F401
import shutil, tempfile, unittest
from pathlib import Path

from director import platforms
from director.studio import art, engine


class TestTemplate(unittest.TestCase):
    def test_it_is_catalogued_ready_and_always_labelled_simplified(self):
        self.assertTrue(art.production_ready('watch_movement'))
        sc = art.scene_visual('watch_movement', {'explode_at': 2.0}, 'tk-bone', 5.0)
        self.assertEqual(sc['theme'], 'tk-ink')                           # metal on a dark ground
        self.assertTrue(any(e.get('text') == art.DRAWING_NOTE for e in sc['elements']))
        mv = next(e for e in sc['elements'] if e['type'] == 'movement3d')
        self.assertEqual((mv['explode_at'], mv['depth']), (2.0, 0))
        self.assertEqual([c['name'] for c in sc['sfx']], ['watch_run', 'whoosh'])


HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()


@unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
class TestRender(unittest.TestCase):
    def test_it_draws_runs_and_separates(self):
        from PIL import Image, ImageChops
        sc = art.scene_visual('watch_movement', {'explode_at': 2.0}, 'tk-ink', 4.0)
        sc['dur'] = 4.0
        sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': [sc]}
        with tempfile.TemporaryDirectory() as d:
            a, b, c = engine.stills(sb, Path(d) / 'one', [0.5, 0.75, 3.9], scale=0.5)
            again = engine.stills(sb, Path(d) / 'two', [0.75], scale=0.5)[0]
            im = [Image.open(p).convert('RGB') for p in (a, b, c, again)]
            gold = sum(1 for px in im[0].crop((0, 150, 360, 500)).get_flattened_data() if px[0] > 150 and px[1] > 110 and px[2] < 110)
            self.assertGreater(gold, 500)                                      # brass wheels on screen
            moved = ImageChops.difference(im[0], im[1]).getbbox()
            self.assertIsNotNone(moved)                                        # the balance swings, the train steps
            self.assertIsNone(ImageChops.difference(im[1], im[3]).getbbox())   # the same time draws the same frame
            self.assertGreater(sum(1 for px in ImageChops.difference(im[1], im[2]).get_flattened_data() if max(px) > 40), 5000)   # exploded
            safe = engine.safe(sb, Path(d), platforms.zones(platforms.get('reels')[1]))
        self.assertIn("nothing under the app's buttons", safe[-1])
