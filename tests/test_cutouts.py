"""Paper cut-outs (rule 12h): the whole subject cut out of its photo; a person no photo shows whole is drawn in the
paper style, labelled, and never evidence; a watch is never drawn (the films are for collectors)."""
from tests import _guard  # noqa: F401
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

from director import quickfilm
from director.studio import art, drawn, engine


class TestDrawn(unittest.TestCase):
    def test_people_are_drawn_and_watches_cannot_be(self):
        for k in drawn.DRESS:
            svg, w, h = drawn.person(k, uid='p')
            self.assertTrue(svg.startswith('<svg') and 'feDropShadow' in svg, k)
            self.assertEqual((w, h), (300, 900), k)
        self.assertFalse(hasattr(drawn, 'watch'))

    def test_the_template_cuts_out_draws_a_person_and_refuses_a_drawn_watch(self):
        sc = art.scene_visual('paper_cutout', {'asset': 'w', 'aspect': 0.5, 'credit': 'A · CC BY-SA 4.0 · cut out'}, 'tk-bone', 4)
        cut = next(e for e in sc['elements'] if e['type'] == 'cutout')
        self.assertEqual((cut['asset'], cut['aspect']), ('w_cut', 0.5))
        self.assertLessEqual(cut['h'] * cut['aspect'], 600)
        sc = art.scene_visual('paper_cutout', {'drawn': {'kind': 'scientist'}, 'card': 'x'}, 'tk-bone', 4)
        self.assertTrue(any(e['type'] == 'svg' for e in sc['elements']))
        self.assertTrue(any(e.get('text') == art.DRAWN_NOTE for e in sc['elements']))
        for p in ({'drawn': {'kind': 'radiomir'}}, {}):
            with self.assertRaises(ValueError):
                art.scene_visual('paper_cutout', p, 'tk-bone', 4)

    def test_a_drawing_is_a_picture_but_never_evidence_and_never_a_watch(self):
        base = {'brand': 'timekeeper', 'lines': [{'id': 'l1', 'text': 'في Florence، عام 1860.', 'template': 'city_zoom', 'params': {'city': 'florence'}}]}
        f = json.loads(json.dumps(base))
        f['lines'].append({'id': 'l2', 'text': 'وكانت عالمة.', 'template': 'paper_cutout', 'params': {'drawn': {'kind': 'scientist'}}})
        self.assertEqual([m for m in quickfilm.story_check(f) if m.startswith('l2')], [])
        f['lines'][1]['event'] = True
        self.assertTrue(any('historical event' in m for m in quickfilm.story_check(f)))
        f['lines'][1].update(event=False, params={'drawn': {'kind': 'radiomir'}})
        self.assertTrue(any(m.startswith('l2') and 'never drawn' in m for m in quickfilm.story_check(f)))


def _rembg():
    py = os.environ.get('VD_CUTOUT_PYTHON', sys.executable)
    return subprocess.run([py, '-c', 'import rembg'], capture_output=True).returncode == 0


@unittest.skipUnless(shutil.which('ffmpeg') and _rembg(), 'rembg not installed (set VD_CUTOUT_PYTHON)')
class TestCutoutTool(unittest.TestCase):
    def test_a_subject_inside_the_photo_is_whole_and_one_cut_by_the_edge_is_not(self):
        from PIL import Image, ImageDraw
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, box in (('inside', (120, 80, 280, 320)), ('edge', (250, 80, 400, 320))):
                im = Image.new('RGB', (400, 400), (210, 205, 195)); dr = ImageDraw.Draw(im)
                dr.ellipse(box, fill=(30, 30, 30)); dr.rectangle((box[0] + 40, box[1] + 60, box[2] - 40, box[3] - 60), fill=(200, 160, 80))
                im.save(d / f'{name}.jpg')
            py = os.environ.get('VD_CUTOUT_PYTHON', sys.executable)
            out = {n: json.loads(subprocess.run([py, str(engine.ROOT / 'tools/cutout_photo.py'), str(d / f'{n}.jpg'), str(d / f'{n}.png')],
                                                capture_output=True, text=True).stdout.strip().splitlines()[-1]) for n in ('inside', 'edge')}
        self.assertTrue(out['inside']['whole']); self.assertFalse(out['edge']['whole'])
        self.assertIn('right', out['edge']['cut_sides'])


if __name__ == '__main__':
    unittest.main()
