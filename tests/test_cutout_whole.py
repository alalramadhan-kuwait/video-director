"""The owner, of Halter in a white coat on a light grey ground with half his coat and his legs gone: «Why did you part
of him is missing. It is repeated issue». A drawing on a flat ground is cut by its colour (nothing inside is lost), and
a remover's cut of a person with holes or in pieces is not whole."""
from tests import _guard  # noqa: F401
import json, subprocess, sys, tempfile, unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/cutout_photo.py'


def figure(path):
    """A sticker-edged figure on a flat light grey ground: a white coat and grey trousers close to the ground's grey."""
    im = Image.new('RGB', (400, 800), (210, 206, 204)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((110, 60, 290, 760), 30, fill=(245, 235, 215))          # the sticker's cream edge
    d.rectangle((125, 80, 275, 470), fill=(240, 240, 238))                        # the white coat
    d.rectangle((140, 470, 260, 740), fill=(205, 203, 201))                       # trousers almost the ground's colour
    d.ellipse((165, 90, 235, 160), fill=(200, 160, 130))                          # the face
    im.save(path)


class Cutout(unittest.TestCase):
    def test_a_drawing_on_a_flat_ground_stays_whole(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d) / 'f.png', Path(d) / 'cut.png'; figure(src)
            r = subprocess.run([sys.executable, str(TOOL), str(src), str(out), '--person'], capture_output=True, text=True)
            rec = json.loads(r.stdout.strip().splitlines()[-1])
            self.assertEqual(rec['method'], 'flat ground'); self.assertTrue(rec['whole'])
            a = np.asarray(Image.open(out))[..., 3] > 128
            h = a.shape[0]; low, high = a[int(h * .62):int(h * .9)].mean(), a[int(h * .15):int(h * .5)].mean()
            self.assertGreater(low, .7 * high)                                   # the trousers are as solid as the coat
            self.assertEqual(int((~a[int(h * .1):int(h * .9), int(a.shape[1] * .3):int(a.shape[1] * .7)]).sum()), 0)   # no hole inside

    def test_holes_and_pieces_make_a_person_not_whole(self):
        src = TOOL.read_text(encoding='utf-8')
        ns = {'np': np, 'ndimage': __import__('scipy.ndimage', fromlist=['x'])}; exec(src[src.index('FLAT ='):src.index('ap = argparse')], ns)
        m = np.zeros((200, 100), bool); m[10:190, 20:80] = True
        self.assertIsNone(ns['broken'](m))
        holed = m.copy(); holed[100:150, 30:70] = False
        self.assertIn('holes', ns['broken'](holed))
        pieces = m.copy(); pieces[100:110, :] = False
        self.assertIn('pieces', ns['broken'](pieces))


if __name__ == '__main__':
    unittest.main()
