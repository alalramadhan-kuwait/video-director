"""Paper cut-outs (rule 12h): the whole subject cut out of its photo, or drawn in the paper style when no photo shows
it whole; a drawing is labelled and is never evidence."""
from tests import _guard  # noqa: F401
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

from director import quickfilm
from director.studio import art, drawn, engine


class TestDrawn(unittest.TestCase):
    def test_every_kind_draws_paper_pieces_with_western_digits(self):
        for k in ('radiomir', 'luminor', 'oyster', 'round'):
            svg, w, h = drawn.watch(k, uid='t')
            self.assertTrue(svg.startswith('<svg') and 'feDropShadow' in svg, k)
            self.assertNotRegex(svg, '[٠-٩]')
        self.assertIn('>12<', drawn.watch('radiomir')[0]); self.assertIn('>XII<', drawn.watch('oyster')[0])
        for k in drawn.DRESS:
            svg, w, h = drawn.person(k, uid='p')
            self.assertEqual((w, h), (300, 900), k)

    def test_the_template_cuts_out_or_draws_and_labels_the_drawing(self):
        sc = art.scene_visual('paper_cutout', {'asset': 'w', 'aspect': 0.5, 'credit': 'A · CC BY-SA 4.0 · cut out'}, 'tk-bone', 4)
        cut = next(e for e in sc['elements'] if e['type'] == 'cutout')
        self.assertEqual((cut['asset'], cut['aspect']), ('w_cut', 0.5))
        self.assertLessEqual(cut['h'] * cut['aspect'], 600)
        sc = art.scene_visual('paper_cutout', {'drawn': {'kind': 'radiomir'}, 'card': 'x'}, 'tk-bone', 4)
        self.assertTrue(any(e['type'] == 'svg' for e in sc['elements']))
        self.assertTrue(any(e.get('text') == art.DRAWN_NOTE for e in sc['elements']))

    def test_a_drawing_is_a_picture_but_never_evidence(self):
        base = {'brand': 'timekeeper', 'lines': [{'id': 'l1', 'text': 'في Florence، عام 1860.', 'template': 'city_zoom', 'params': {'city': 'florence'}}]}
        f = json.loads(json.dumps(base))
        f['lines'].append({'id': 'l2', 'text': 'وصنعت ساعة للغطّاسين.', 'template': 'paper_cutout', 'params': {'drawn': {'kind': 'radiomir'}}})
        self.assertEqual([m for m in quickfilm.story_check(f) if m.startswith('l2')], [])
        f['lines'][1]['event'] = True
        self.assertTrue(any('historical event' in m for m in quickfilm.story_check(f)))


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
