"""The measured quality bar (director/quality.py) and the spoken caption word in gold."""
from tests import _guard  # noqa: F401
import shutil, subprocess, tempfile, unittest
from pathlib import Path

from director import brand as B, quality
from director.studio import art, engine


class TestMeasures(unittest.TestCase):
    def test_contrast_ratio_follows_wcag(self):
        self.assertAlmostEqual(quality.ratio((0, 0, 0), (255, 255, 255)), 21.0, places=1)
        self.assertAlmostEqual(quality.ratio((255, 255, 255), (255, 255, 255)), 1.0)
        self.assertEqual(quality.need({'px': 40, 'weight': 700}), 3.0)
        self.assertEqual(quality.need({'px': 18, 'weight': 400}), 4.5)
        self.assertEqual(quality.need({'px': 20, 'weight': 800}), 3.0)

    def test_the_brand_gold_stays_readable_on_both_caption_tags(self):
        cap = B.style({'caption': {}}, 'timekeeper')['caption']
        hx = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        self.assertGreaterEqual(quality.ratio(hx(cap['active']), hx(cap['bg'])), 4.5)            # gold on the black tag
        self.assertGreaterEqual(quality.ratio(hx(cap['activeLight']), hx('#F3F0E8')), 4.5)      # dark gold on the light tag

    def test_runs_join_samples_and_say_where(self):
        found = [{'kind': 'contrast', 't': t, 'scene': 2, 'what': 'كلمة', 'ratio': 2.0 + t / 10, 'need': 3.0} for t in (4.5, 5.5, 6.5)]
        lines = quality.runs(found)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('scene 3  4.5-6.5s'))
        self.assertIn('2.45:1', lines[0])


HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()


@unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
class TestOnRenders(unittest.TestCase):
    def _sb(self, *els, dur=3.0, theme='tk-bone'):
        sc = art.scene_visual('kinetic_type', {'lines': []}, theme, dur)
        sc.update(dur=dur, elements=list(els))
        return {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': [sc]}

    def test_faint_words_and_words_over_words_are_found_and_good_words_pass(self):
        good = {'type': 'text', 'text': 'كلمة واضحة', 'font': 'title', 'size': 60, 'color': '#111111', 'x': 360, 'y': 400}
        faint = {'type': 'text', 'text': 'كلمة باهتة', 'font': 'cap', 'size': 22, 'color': '#C9C3B4', 'x': 360, 'y': 700}
        over = {'type': 'text', 'text': 'فوقها كلام', 'font': 'title', 'size': 60, 'color': '#111111', 'x': 370, 'y': 410}
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(quality.check(self._sb(good), Path(d), 3.0), [])
            lines = quality.check(self._sb(good, faint, over), Path(d), 3.0)
        self.assertTrue(any('كلمة باهتة' in l and 'hard to read' in l for l in lines), lines)
        self.assertTrue(any('crosses' in l for l in lines), lines)

    def test_frame_one_must_be_finished(self):
        late = {'type': 'text', 'text': 'تدخل متأخرة', 'font': 'title', 'size': 60, 'color': '#111111', 'x': 360, 'y': 400,
                'opacity': [[0, 0.5], [1.0, 1]]}
        with tempfile.TemporaryDirectory() as d:
            lines = quality.check(self._sb(late), Path(d), 3.0)
        self.assertTrue(any('frame one' in l for l in lines), lines)

    def test_a_still_stretch_in_the_film_is_found(self):
        with tempfile.TemporaryDirectory() as d:
            mp4 = Path(d) / 'f.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=size=180x320:rate=15:duration=2', '-f', 'lavfi', '-i',
                            'color=c=gray:size=180x320:rate=15:duration=2', '-filter_complex', '[0][1]concat=n=2:v=1', str(mp4)], check=True)
            got = quality.frozen(mp4)
        self.assertEqual(len(got), 1)
        self.assertAlmostEqual(got[0]['t'], 2.0, delta=0.2)

    def test_mixed_arabic_and_latin_reads_right_to_left_and_a_latin_name_is_one_caption(self):
        sc = art.scene_visual('kinetic_type', {'lines': [{'text': 'Radiomir · من راديوم Marie Curie', 'size': 40}]}, 'tk-bone', 3.0)
        sc.update(dur=3.0, banner='Radiomir · من راديوم Marie Curie',
                  words=[[0.2, 'على'], [0.5, 'جسر'], [0.8, 'Ponte'], [1.0, 'alle'], [1.2, 'Grazie']])
        sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': [sc]}
        with tempfile.TemporaryDirectory() as d:
            f = quality.textmap(sb, Path(d), [2.0])[0]
            from director import platforms
            safe = engine.safe(sb, Path(d), platforms.zones(platforms.get('reels')[1]))
        self.assertIn("nothing under the app's buttons", safe[-1])                    # the long name keeps its row on screen
        mixed = [w for w in f['words'] if 'Marie' in w['text']]
        self.assertTrue(mixed and all(w['dir'] == 'rtl' for w in mixed), mixed)           # the banner and the line
        caps = [w['text'] for w in f['words'] if w['caption']]
        self.assertIn('Ponte alle Grazie', caps); self.assertNotIn('alle', caps)

    def test_the_spoken_caption_word_is_gold(self):
        from PIL import Image
        sc = art.scene_visual('kinetic_type', {'lines': []}, 'tk-bone', 3.0)
        sc.update(dur=3.0, words=[[0.2, 'ساعة'], [1.0, 'صُنعت']])
        sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': [sc]}
        with tempfile.TemporaryDirectory() as d:
            a, b = engine.stills(sb, Path(d), [0.6, 1.6], scale=0.5)
            gold = lambda p: sum(1 for px in Image.open(p).convert('RGB').crop((0, 480, 360, 560)).getdata()
                                 if px[0] > 160 and 120 < px[1] < 190 and px[2] < 120)
            ga, gb = gold(a), gold(b)
        self.assertGreater(ga, 30)                 # «ساعة» is being said: gold
        self.assertGreater(gb, 30)                 # «صُنعت» now: still one gold word (the first back to white)


if __name__ == '__main__':
    unittest.main()


class TestBehindOffFrame(unittest.TestCase):
    def test_words_wholly_off_the_frame_have_no_background(self):
        from PIL import Image
        img = Image.new('RGB', (720, 1280), 'white')
        self.assertEqual(quality.behind(img, [800, 100, 900, 160]), [])          # right of the frame (a camera move)
        self.assertEqual(quality.behind(img, [100, 1400, 300, 1460]), [])        # below it
        self.assertTrue(quality.behind(img, [100, 100, 300, 160]))
