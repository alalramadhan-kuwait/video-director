"""The Time Keeper watermark: the monogram alone, top left, on the film and off for the end card (the owner, 4 Nov 2026)."""
from tests import _guard  # noqa: F401
import subprocess, tempfile, unittest
from pathlib import Path

from PIL import Image

from director import brand as B, watermark

LOGO = B.ROOT / 'vendor/paper-story/tk-logo-512.png'


def frame(mp4: Path, t: float) -> Image.Image:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(mp4), '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'],
                         capture_output=True, check=True).stdout
    p = Path(tempfile.mkstemp(suffix='.png')[1]); p.write_bytes(raw); return Image.open(p).convert('RGB')


class TestWatermark(unittest.TestCase):
    def test_the_brand_signs_its_films(self):
        cfg = watermark.config(B.load('timekeeper'))
        self.assertIsNotNone(cfg)
        self.assertIsNone(watermark.config({}))
        self.assertIsNone(watermark.config({'watermark': {'off': True}}))

    def test_the_mark_is_white_top_left_and_clear_of_the_app(self):
        for w, h in ((720, 1280), (1080, 1920)):
            m = watermark.mark(LOGO, w, h)
            self.assertEqual(m.size, (w, h))
            box = m.getchannel('A').getbbox()
            self.assertLess(box[2], w * 0.25)                       # the left quarter: Instagram's buttons are on the right
            self.assertGreater(box[1], h * 150 / 1280 - h * 0.02)   # under the app's top bar (brand safe_area.top)
            self.assertLess(box[3], h * 0.3)
            px = [p for p in m.getdata() if p[3] > 150]
            white = [p for p in px if min(p[:3]) > 230]
            self.assertGreater(len(white), len(px) // 3)                   # white strokes...
            self.assertTrue(any(p[3] > 20 and max(p[:3]) < 60 for p in m.getdata()))   # ...with a thin dark edge
            self.assertFalse(any(200 < min(p[:3]) < 250 and p[3] > 100 and abs(p[0] - p[2]) > 8 for p in px))   # no pale disc
            self.assertLessEqual(max(p[3] for p in m.getdata()), 230)            # about 80 % (with its shadow), never solid

    def test_it_leaves_for_the_end_card(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / 'in.mp4', Path(d) / 'out.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=0x203040:s=360x640:d=2:r=12',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(src)], check=True)
            watermark.apply(src, dst, LOGO, ending=0.6)
            box = watermark.mark(LOGO, 360, 640).getchannel('A').getbbox()
            def bright(t):
                im = frame(dst, t).crop(box); return max(sum(p) for p in im.getdata())
            self.assertGreater(bright(0.3), 400)        # the white mark on the film
            self.assertLess(bright(1.8), 250)           # gone on the end card
            self.assertFalse(Path(d, 'out.mark.png').exists())


if __name__ == '__main__':
    unittest.main()
