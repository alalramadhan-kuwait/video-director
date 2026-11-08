"""The topic as a carousel (the owner: «generate the topic as a carousel instead of video if required… save along
with caption»): the kit's rules, checked before anything is rendered."""
from tests import _guard  # noqa: F401
import shutil, subprocess, tempfile, unittest
from pathlib import Path

from director import carousel

BODY = ' '.join(['كلمة'] * 27)


def spec(n=5, **kw):
    return {'cover': {'top': 'ليش داخل ساعتك', 'bottom': 'ياقوت حقيقي؟', 'image': 'c.jpg'},
            'slides': [{'title': 'النحاس يتآكل', 'body': BODY, 'image': f'{i}.png'} for i in range(n - 1)]
            + [{'title': 'النحاس يتآكل', 'body': BODY, 'image': f'{n - 1}.png', 'ask': 'وأنت شرايك؟'}], **kw}


class Rules(unittest.TestCase):
    def test_a_good_carousel_passes(self):
        self.assertEqual(carousel.check(spec()), [])

    def test_four_or_five_slides_and_a_short_cover(self):
        self.assertTrue(any('written slides' in m for m in carousel.check(spec(3))))
        s = spec(); s['cover']['bottom'] = 'ب' * 70
        self.assertTrue(any('characters in the headline' in m for m in carousel.check(s)))

    def test_a_slide_is_one_idea_in_12_to_32_words(self):
        s = spec(); s['slides'][1]['body'] = 'قصير جدًا'
        self.assertTrue(any(m.startswith('slide 2:') and 'words' in m for m in carousel.check(s)))
        s = spec(); s['slides'][1]['body'] = ' '.join(['كلمة'] * 40)
        self.assertTrue(any(m.startswith('slide 2:') and 'words' in m for m in carousel.check(s)))
        s = spec(); s['slides'][0]['title'] = 'عنوان طويل جدًا من خمس كلمات'
        self.assertTrue(any('a title of' in m for m in carousel.check(s)))

    def test_layouts_never_repeat_and_every_slide_has_its_image(self):
        s = spec(); s['slides'][1]['layout'] = s['slides'][2]['layout'] = 'leftBleed'
        self.assertTrue(any('the same layout' in m for m in carousel.check(s)))
        s = spec(); del s['slides'][0]['image']
        self.assertTrue(any('no image' in m for m in carousel.check(s)))
        self.assertEqual(carousel.layouts(spec()), list(carousel.LAYOUTS))

    def test_a_watch_is_never_bled_off_the_slide(self):
        s = spec(); s['slides'][4].update(watch=True, layout='bigCorner')
        self.assertTrue(any('shown whole' in m for m in carousel.check(s)))
        s['slides'][4]['layout'] = 'topImage'
        self.assertEqual([m for m in carousel.check(s) if 'shown whole' in m], [])

    def test_the_language_holds(self):
        s = spec(); s['slides'][0]['body'] = 'ليش ' + BODY
        self.assertEqual([m for m in carousel.check(s, language='kuwaiti') if 'belong' in m], [])
        self.assertTrue(any('belong' in m for m in carousel.check(s, language='light')))

    def test_a_news_carousel_is_short_text_and_any_length(self):
        s = spec(12, news=True)
        for x in s['slides']: x['body'] = 'سماكتها 1.65 ملم فقط'
        s['slides'][-1]['ask'] = 'أي ساعة؟'
        self.assertEqual([m for m in carousel.check(s) if 'words' in m or 'written slides' in m], [])
        s['slides'][0]['body'] = BODY
        self.assertTrue(any(m.startswith('slide 1:') and 'words' in m for m in carousel.check(s)))

    def test_the_awards_style_is_checked_by_its_own_shape(self):
        card = {'title': 'التوربيون', 'brand': 'X', 'model': 'Y', 'image': 'a.png'}
        s = {'news': True, 'cover': {'top': 'جوائز'}, 'slides': [{'type': 'hero', 'title': 'الإبرة الذهبية', 'image': 'h.png'},
                                                               {'type': 'cards', 'cards': [card] * 6}]}
        self.assertEqual(carousel.check(s), [])
        s['slides'][1]['cards'] = [card] * 7
        self.assertTrue(any('1–6 cards' in m for m in carousel.check(s)))

    def test_a_watch_is_never_a_cut_out(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            Image.new('RGBA', (20, 20), (0, 0, 0, 0)).save(d / 'cut.png')
            Image.new('RGB', (20, 20), 'white').save(d / 'photo.jpg')
            s = spec(); s['slides'][0].update(watch=True, image='cut.png', layout='topImage')
            self.assertTrue(any('cut-out' in m for m in carousel.check(s, d)))
            s['slides'][0]['image'] = 'photo.jpg'
            self.assertEqual([m for m in carousel.check(s, d) if 'cut-out' in m], [])

    def test_missing_images_are_named(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(any('is missing' in m for m in carousel.check(spec(), Path(d))))


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class ReaderQuestion(unittest.TestCase):
    """The owner: «دائما سؤال القارئ يكون أكبر ويشد القارئ»: the last slide asks, in its own large line."""
    def test_the_last_slide_asks_the_reader(self):
        s = spec(); s['slides'][-1].pop('ask')
        self.assertTrue(any("reader's question" in m for m in carousel.check(s)))

    def test_only_the_last_slide_asks(self):
        s = spec(); s['slides'][0]['ask'] = 'ليش؟'
        self.assertTrue(any('only the last slide' in m for m in carousel.check(s)))

    def test_the_renderer_sets_it_large(self):
        src = carousel.RENDERER.read_text(encoding='utf-8')
        self.assertIn('class="ask"', src)
        self.assertIn('.ask{font-size:${SIZE.ask}px', src)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Renderer(unittest.TestCase):
    def test_the_renderer_parses(self):
        r = subprocess.run(['node', '--check', str(carousel.RENDERER)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((carousel.RENDERER.parent / 'fonts/tajawal-arabic-800-normal.woff2').is_file())


class WholeWatch(unittest.TestCase):
    """The owner, of a movement cut off a slide: «محرك جزا كبير منه رايح». A layout the check allows for a watch keeps
    its picture inside the 1080×1350 slide; bottomImage alone bleeds 60 px off the bottom."""
    def test_a_watch_picture_stays_inside_the_slide(self):
        import re
        src = carousel.RENDERER.read_text(encoding='utf-8')
        whole = re.search(r'const WHOLE = \{(.*?)\n\};', src, re.S).group(1)
        boxes = dict(re.findall(r"(\w+): '([^']+)'", whole))
        self.assertEqual(set(boxes), {'topImage', 'bottomImage'})
        for name, css in boxes.items():
            v = {k: int(n) for k, n in re.findall(r'(left|top|bottom|width|height):(-?\d+)px', css)}
            self.assertGreaterEqual(v['left'], 0, name)
            self.assertLessEqual(v['left'] + v['width'], 1080, name)
            top = v['top'] if 'top' in v else 1350 - v['bottom'] - v['height']
            self.assertGreaterEqual(top, 0, name)
            self.assertLessEqual(top + v['height'], 1350, name)
        self.assertIn('s.watch && WHOLE[name]', src)


if __name__ == '__main__':
    unittest.main()


class TextSize(unittest.TestCase):
    """The owner: «the size of the text, it is small… increase it about 10%». One size table in the renderer, the same
    in the studio's editor, each at least 10% over the old (title 74, body 40, question 58, name 28, number 30, cover 78)."""
    OLD = {'title': 74, 'body': 40, 'ask': 58, 'name': 28, 'num': 30, 'cover': 78}

    @staticmethod
    def table(src, pat):
        import re
        return {k: int(v) for k, v in re.findall(r'(\w+): (\d+)', re.search(pat, src).group(1))}

    def test_ten_percent_bigger_and_the_editor_in_step(self):
        mjs = self.table(carousel.RENDERER.read_text(encoding='utf-8'), r'const SIZE = \{([^}]*)\}')
        page = (carousel.RENDERER.parents[2] / 'studio-page/index.html').read_text(encoding='utf-8')
        kit = self.table(page, r'SIZE: \{([^}]*)\}')
        self.assertEqual(mjs, kit)
        for k, old in self.OLD.items():
            self.assertGreaterEqual(mjs[k], round(old * 1.09), k)


@unittest.skipUnless(shutil.which('node'), 'node is not installed')
class Fit(unittest.TestCase):
    """Bigger text takes room from the picture (topImage, bottomImage); when the picture would be squeezed too small,
    or the text runs off the slide, the renderer says so (WARN), and make.py prints it."""
    def render(self, body, layout='topImage'):
        from PIL import Image
        d = Path(tempfile.mkdtemp())
        Image.new('RGB', (800, 600), 'gray').save(d / 'p.png'); Image.new('RGB', (1080, 1350), 'gray').save(d / 'c.jpg')
        s = {'cover': {'top': 'ليش', 'bottom': 'ياقوت؟', 'image': 'c.jpg'}, 'slides': [{'title': 'عنوان قصير', 'body': body, 'image': 'p.png', 'layout': layout}]}
        (d / 'spec.json').write_text(__import__('json').dumps(s, ensure_ascii=False), encoding='utf-8')
        try:
            return carousel.render_report(d / 'spec.json', d / 'out')
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.skipTest(f'no browser to render with: {e}')

    def test_a_normal_slide_fits(self):
        files, warns = self.render(' '.join(['كلمة'] * 30))
        self.assertEqual(len(files), 2); self.assertEqual(warns, [])

    def test_too_much_text_is_named(self):
        for layout in ('topImage', 'bottomImage'):
            files, warns = self.render(' '.join(['كلمة طويلة'] * 60), layout)
            self.assertTrue(any(w.startswith('slide 1:') for w in warns), (layout, warns))
