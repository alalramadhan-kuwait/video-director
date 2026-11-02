"""The topic as a carousel (the owner: «generate the topic as a carousel instead of video if required… save along
with caption»): the kit's rules, checked before anything is rendered."""
from tests import _guard  # noqa: F401
import shutil, subprocess, tempfile, unittest
from pathlib import Path

from director import carousel

BODY = ' '.join(['كلمة'] * 27)


def spec(n=5, **kw):
    return {'cover': {'top': 'ليش داخل ساعتك', 'bottom': 'ياقوت حقيقي؟', 'image': 'c.jpg'},
            'slides': [{'title': 'النحاس يتآكل', 'body': BODY, 'image': f'{i}.png'} for i in range(n)], **kw}


class Rules(unittest.TestCase):
    def test_a_good_carousel_passes(self):
        self.assertEqual(carousel.check(spec()), [])

    def test_four_or_five_slides_and_a_short_cover(self):
        self.assertTrue(any('written slides' in m for m in carousel.check(spec(3))))
        s = spec(); s['cover']['bottom'] = 'ب' * 70
        self.assertTrue(any('characters in the headline' in m for m in carousel.check(s)))

    def test_a_slide_is_one_idea_in_25_to_32_words(self):
        s = spec(); s['slides'][1]['body'] = 'قصير جدًا'
        self.assertTrue(any(m.startswith('slide 2:') and 'words' in m for m in carousel.check(s)))
        s = spec(); s['slides'][0]['title'] = 'عنوان طويل جدًا من خمس كلمات'
        self.assertTrue(any('a title of' in m for m in carousel.check(s)))

    def test_layouts_never_repeat_and_every_slide_has_its_image(self):
        s = spec(); s['slides'][1]['layout'] = s['slides'][2]['layout'] = 'leftBleed'
        self.assertTrue(any('the same layout' in m for m in carousel.check(s)))
        s = spec(); del s['slides'][0]['image']
        self.assertTrue(any('no image' in m for m in carousel.check(s)))
        self.assertEqual(carousel.layouts(spec()), list(carousel.LAYOUTS))

    def test_the_language_holds(self):
        s = spec(); s['slides'][0]['body'] = 'ليش ' + BODY
        self.assertEqual([m for m in carousel.check(s, language='kuwaiti') if 'belong' in m], [])
        self.assertTrue(any('belong' in m for m in carousel.check(s, language='light')))

    def test_missing_images_are_named(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(any('is missing' in m for m in carousel.check(spec(), Path(d))))


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Renderer(unittest.TestCase):
    def test_the_renderer_parses(self):
        r = subprocess.run(['node', '--check', str(carousel.RENDERER)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((carousel.RENDERER.parent / 'fonts/tajawal-arabic-800-normal.woff2').is_file())


if __name__ == '__main__':
    unittest.main()
