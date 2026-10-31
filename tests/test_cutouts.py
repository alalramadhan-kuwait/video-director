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
        sc = art.scene_visual('paper_cutout', {'asset': 'w', 'aspect': 0.5, 'credit': 'A · CC BY-SA 4.0'}, 'tk-bone', 4)
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



class TestTheUncutPhotoAndItsCredit(unittest.TestCase):
    """A watch the photo cuts is shown as its photo, uncut; `in: none` puts it on screen from frame 0; the credit on
    screen is the photo's own, with no English jargon added (Étienne v10: «cut out» leaked onto every person scene)."""
    PICS = {'w': {'credit': 'A · CC BY-SA 4.0', 'aspect': 1.2}, 'p': {'credit': 'B · CC BY 2.0'}}
    FILM = {'photos': {'w': {'query': 'x'}, 'p': {'query': 'y', 'person': True}}}

    def _run(self, params, whole):
        from unittest import mock
        with mock.patch.object(quickfilm, 'cutout', return_value={'whole': whole, 'aspect': .6, 'why': 'cut'}):
            report = {}
            return (*quickfilm.cut_or_uncut({'id': 'l1'}, dict(params), self.FILM, self.PICS, Path('.'), report), report)

    def test_a_cut_watch_falls_back_to_its_photo_and_keeps_its_entrance(self):
        template, params, report = self._run({'asset': 'w', 'desc': 'd', 'card': 'c', 'print': True, 'w': 380, 'y': 520,
                                              'in': 'none', 'tilt': 3}, whole=False)
        self.assertEqual(template, 'archive_photo')
        self.assertEqual(params['in'], 'none')
        self.assertNotIn('tilt', params)
        self.assertIn('in', quickfilm.UNCUT_KEYS)
        self.assertEqual(params['credit'], 'A · CC BY-SA 4.0')
        self.assertTrue(report['drawn'])
        photo = next(e for e in art.scene_visual(template, params, 'tk-ink', 5.0)['elements'] if e['type'] == 'photo')
        self.assertNotIn('in', photo)                                               # on screen from frame 0

    def test_a_direct_archive_photo_takes_its_entrance(self):
        p = {'asset': 'w', 'desc': 'd', 'print': True, 'aspect': 1.2}
        photo = lambda **k: next(e for e in art.scene_visual('archive_photo', {**p, **k}, 'tk-ink', 5.0)['elements'] if e['type'] == 'photo')
        self.assertEqual(photo()['in'], {'type': 'drop', 'at': .15})                 # the default: dropped onto the desk
        self.assertNotIn('in', photo(**{'in': 'none'}))
        self.assertEqual(photo(**{'in': {'type': 'fade', 'at': 0}})['in'], {'type': 'fade', 'at': 0})

    def test_no_cut_out_jargon_in_any_credit_on_screen(self):
        for params, whole in (({'asset': 'p', 'desc': 'd'}, True), ({'asset': 'w', 'desc': 'd'}, True), ({'asset': 'w', 'desc': 'd'}, False)):
            template, out, _ = self._run(params, whole)
            self.assertNotIn('cut out', out.get('credit', ''), (params, whole))
            texts = [e.get('text', '') for e in art.scene_visual(template, {**out, 'aspect': out.get('aspect', .6)}, 'tk-bone', 4.0)['elements']]
            self.assertFalse(any('cut out' in t for t in texts), texts)
            self.assertTrue(any(t.startswith(self.PICS[params['asset']]['credit'][:1]) for t in texts), texts)
        self.assertNotIn("' · cut out'", (engine.ROOT / 'director/quickfilm.py').read_text(encoding='utf-8'))

class TestTheNamedModelIsTheModelShown(unittest.TestCase):
    """Rule 12i: in the watch community a model that does not match its picture is a big thing."""
    def _film(self, line, **photo):
        return {'brand': 'timekeeper', 'photos': {'w': {'query': 'x', **photo}},
                'lines': [{'id': 'l1', 'text': 'في Florence، عام 1860.', 'template': 'city_zoom', 'params': {'city': 'florence'}},
                          {'id': 'l2', 'template': 'archive_photo', **line}]}

    def _faults(self, film):
        return [m for m in quickfilm.story_check(film) if m.startswith('l2') and ('names' in m)]

    def test_a_radiomir_under_the_word_luminor_is_caught(self):
        f = self._film({'text': 'ثم سجّلت Panerai مادة سمّتها Luminor.', 'banner': 'Luminor · 1949', 'params': {'asset': 'w', 'card': 'Luminor'}},
                       watch='Panerai Radiomir 8 giorni')
        self.assertTrue(any('Luminor' in m and 'Radiomir' in m for m in self._faults(f)), quickfilm.story_check(f))

    def test_the_right_model_passes_and_the_longest_name_wins(self):
        f = self._film({'text': 'ثم جاءت Royal Oak Offshore.', 'params': {'asset': 'w', 'card': 'Royal Oak Offshore'}},
                       watch='Audemars Piguet Royal Oak Offshore 25721')
        self.assertEqual(self._faults(f), [])
        f = self._film({'text': 'ثم جاءت Royal Oak Offshore.', 'params': {'asset': 'w'}}, watch='Audemars Piguet Royal Oak 5402')
        self.assertTrue(self._faults(f))

    def test_a_photo_under_a_named_model_must_say_what_it_shows(self):
        f = self._film({'text': 'ثم جاءت Submariner.', 'params': {'asset': 'w'}})
        self.assertTrue(any("say what photo 'w' shows" in m for m in self._faults(f)))
        f = self._film({'text': 'ثم جاءت Submariner.', 'params': {'asset': 'w'}}, not_a_watch=True)
        self.assertEqual(self._faults(f), [])

    def test_the_watch_is_named_on_screen_with_its_credit(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); (d / 'assets').mkdir()
            from PIL import Image
            Image.new('RGB', (40, 30)).save(d / 'assets' / 'w.jpg')
            (d / 'assets' / 'w.licence.json').write_text(json.dumps({'credit': 'A · CC BY 2.0', 'licence': 'CC BY 2.0'}))
            pics = quickfilm.photos({'photos': {'w': {'query': 'x', 'watch': 'Rolex Oyster · 1926'}}}, d)
        self.assertEqual(pics['w']['credit'], 'Rolex Oyster · 1926 · A · CC BY 2.0')

    def test_a_long_credit_keeps_the_watch_author_and_licence_whole(self):
        t = art.short_credit('Panerai Luminor Marina PAM 111 · modern · Daniel Zimmermann from Bayern, Deutschland (Germany) · CC BY 2.0 · Wikimedia Commons')
        self.assertEqual(t, 'Panerai Luminor Marina PAM 111 · modern · Daniel Zimmermann · CC BY 2.0 · Commons')
        self.assertEqual(art.short_credit('Clyde94 · CC BY-SA 4.0 · Wikimedia Commons'), 'Clyde94 · CC BY-SA 4.0 · Wikimedia Commons')

    def test_the_panerai_film_keeps_the_rule(self):
        import yaml
        film = yaml.safe_load((engine.ROOT / 'films' / 'panerai.yaml').read_text(encoding='utf-8'))
        self.assertEqual([m for m in quickfilm.story_check(film) if 'names' in m], [])


class TestCreditedPhotos(unittest.TestCase):
    """Rule 12j: a real photo from wherever it is best, credited; never in the public repository."""
    def test_a_web_photo_needs_its_page_and_credit(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                quickfilm.photos({'photos': {'w': {'url': 'https://example.com/w.jpg'}}}, Path(d))

    def test_the_owners_file_is_credited_and_a_missing_one_waits(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); Image.new('RGB', (40, 30)).save(d / 'mine.jpg')
            pics = quickfilm.photos({'photos': {'w': {'file': str(d / 'mine.jpg'), 'licence': 'credited', 'credit': 'product photo'},
                                                'gone': {'file': str(d / 'nowhere.jpg'), 'licence': 'credited', 'credit': 'x'}}}, d / 'work')
        self.assertTrue(pics['w']['credited']); self.assertEqual(pics['w']['credit'], 'product photo')
        self.assertTrue(pics['gone']['missing'])

    def test_a_phone_photo_is_turned_upright(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'p.jpg'
            im = Image.new('RGB', (60, 20)); ex = im.getexif(); ex[0x0112] = 6; im.save(f, exif=ex)
            quickfilm._upright(f)
            with Image.open(f) as up:
                self.assertEqual(up.size, (20, 60))

    def test_private_photos_never_enter_git(self):
        r = subprocess.run(['git', 'check-ignore', 'films/private/pam111.jpg'], cwd=engine.ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


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
