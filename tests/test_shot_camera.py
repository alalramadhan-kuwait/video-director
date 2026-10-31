"""Bang Motion's camera ideas, kept as rules: shot sizes framed on what the words are about (never below zoom 1.08,
never a photo shown bigger than its pixels allow), the camera crossing the cut (push-through, match, whip, right to
left for Arabic), directional motion blur on fast moves with asymmetric entrances and exits, and the stage law."""
from tests import _guard  # noqa: F401
import shutil, tempfile, unittest
from pathlib import Path

import numpy as np

from director import quality, quickfilm
from director.studio import art, engine, motion, sets

HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()
WORDS = [[0.5, 'ساعة'], [1.6, 'بيعت'], [2.8, 'مزاد'], [3.9, 'دينار'], [5.2, 'كويتي']]


def _zooms(sc, dur, n=60):
    return [motion.val(sc['camera']['zoom'], dur * i / n, 1.0) for i in range(n + 1)]


class TestShotSizes(unittest.TestCase):
    def test_a_scene_changes_shot_size_on_its_words_and_never_rests_below_the_floor(self):
        for seed in ('l1', 'l2', 'l3', 'l4', 'l5', 'l6'):
            sc = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .5, 'person': True}, 'tk-bone', 7.5, seed=seed)
            motion.direct(sc, 7.5, seed, words=WORDS, pixels={'h_cut': (1700, 2500)}, template='paper_cutout')
            shots = sc['camera']['shots']
            self.assertGreaterEqual(len(shots), 2, seed)
            self.assertTrue(all(a['size'] != b['size'] for a, b in zip(shots, shots[1:])), shots)   # never the same size twice
            self.assertTrue({'close', 'face'} & {s['size'] for s in shots}, shots)               # a person opens on a face (18j)
            self.assertGreaterEqual(min(_zooms(sc, 7.5)), motion.FLOOR - 1e-6)
            self.assertGreaterEqual(max(_zooms(sc, 7.5)), 1.6)                                      # a real close-up, not 3 %
            self.assertTrue(any(abs(s['at'] - t) < .01 for s in shots[1:] for t, _ in WORDS))       # on a spoken word
            self.assertTrue(sc['camera']['clamp'])
        a = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .5, 'person': True}, 'tk-bone', 7.5, seed='x')
        b = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .5, 'person': True}, 'tk-bone', 7.5, seed='x')
        for sc in (a, b): motion.direct(sc, 7.5, 'x', words=WORDS)
        self.assertEqual(a['camera'], b['camera'])                                                   # seeded by the line

    def test_a_person_is_met_face_first_then_the_place(self):
        """Rule 18j: a person scene opens close on the face, then pulls back wide."""
        for seed in ('l1', 'l2', 'l3'):
            sc = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .5, 'person': True}, 'tk-bone', 7.0, seed=seed)
            motion.direct(sc, 7.0, seed, words=WORDS, pixels={'h_cut': (1700, 2500)}, template='paper_cutout')
            shots = sc['camera']['shots']
            self.assertEqual(shots[0]['size'], 'face', seed); self.assertEqual(shots[1]['size'], 'wide', seed)
            self.assertGreaterEqual(shots[0]['zoom'], 2.0, seed)                                        # the face fills the frame
            self.assertLess(shots[0]['focus'][1], motion.hero(sc)['cy'])                              # on the face

    def test_a_person_is_framed_on_the_face_and_the_frame_edge_never_shows(self):
        sc = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .5, 'person': True}, 'tk-bone', 6.0, seed='l1')
        h = motion.hero(sc)
        self.assertTrue(h['person']); self.assertLess(h['fy'], h['cy'] - h['h'] * .25)               # the face, not the waist
        motion.direct(sc, 6.0, 'l1', words=WORDS)
        cam = sc['camera']
        for i in range(61):
            t = 6.0 * i / 60
            z, x, y = (motion.val(cam[k], t, d) for k, d in (('zoom', 1), ('x', 360), ('y', 640)))
            self.assertLessEqual(360 - x * z, 0.6); self.assertGreaterEqual(360 + (720 - x) * z, 719.4)
            self.assertLessEqual(640 - y * z, 0.6); self.assertGreaterEqual(640 + (1280 - y) * z, 1279.4)

    def test_a_line_steers_the_camera_onto_a_detail_on_its_word(self):
        sc = art.scene_visual('product_macro', {'asset': 'w', 'desc': 'd'}, 'tk-bone', 8.0, seed='l6a')
        words = [[1.0, 'وهي'], [2.4, 'فبراير'], [6.1, 'مسامير']]
        shots = [{True: 'فبراير', 'to': 'close', 'focus': [520, 610]}, {'on': 'مسامير', 'to': 'medium'}]   # YAML reads on: as True
        motion.direct(sc, 8.0, 'l6a', words=words, shots=shots, pixels={'w': (3000, 3400)})
        s = sc['camera']['shots']
        self.assertEqual([x['size'] for x in s], ['wide', 'close', 'medium'])
        self.assertEqual(s[1]['at'], 2.4); self.assertEqual(s[1]['focus'], [520, 610])
        arrive = 2.4 - motion.LEAD + motion.MOVE
        z = motion.val(sc['camera']['zoom'], arrive, 1)
        self.assertGreaterEqual(z, 1.6)
        sx, sy, _ = motion.screen_point(sc, arrive, 520, 610)                                        # the detail is in frame,
        self.assertTrue(200 < sx < 720 and 300 < sy < 980)                                           # near the middle
        self.assertGreaterEqual(motion.val(sc['camera']['zoom'], 1.0, 1), motion.FLOOR)
        self.assertEqual(motion.val(sc['camera']['zoom'], 2.0, 1) < z, True)                         # it moves in on the word

    def test_words_on_the_screen_steer_the_shot_and_a_number_with_its_unit_is_the_price(self):
        sc = art.scene_visual('stat_counter', {'value': 71400, 'label': 'دينار كويتي', 'title': 'بيعت في مزاد'}, 'tk-ink', 7.0, seed='l0')
        motion.direct(sc, 7.0, 'l0', words=[[1.0, 'بيعت'], [3.2, 'دينار']], shots=[{'on': 'دينار', 'to': 'close'}])
        s = sc['camera']['shots'][-1]
        self.assertEqual(s['at'], 3.2)
        self.assertTrue(640 < s['focus'][1] < 735)                                                   # between the number and «دينار»
        self.assertLessEqual(max(_zooms(sc, 7.0)), motion.DRAWN_MAX + 1e-6)                          # a drawn canvas stays sharp

    def test_a_picture_scene_keeps_its_words_on_the_screen(self):
        sc = art.scene_visual('archive_photo', {'asset': 'w', 'desc': 'd', 'aspect': 1.4, 'card': 'آلة ساعة برج'}, 'tk-bone', 6.0)
        motion.direct(sc, 6.0, 'l2', words=[[2.5, 'برج']])
        card = next(e for e in sc['elements'] if e['type'] == 'card')
        self.assertEqual(card['depth'], 0); self.assertGreaterEqual(card['z'], motion.HUD)
        self.assertNotEqual(sc['camera']['shots'][-1]['focus'][1], card['y'])                         # «برج» frames the photo

    def test_templates_that_fly_their_own_camera_keep_it(self):
        sc = art.scene_visual('city_zoom', {'city': 'paris'}, 'tk-bone', 6.0)
        before = dict(sc['camera'])
        motion.direct(sc, 6.0, 'l', template='city_zoom')
        self.assertEqual(sc['camera']['zoom'], before['zoom']); self.assertEqual(sc['camera']['own'], 'city_zoom')


class TestZoomCap(unittest.TestCase):
    def _shown(self, sc, e, nw, nh, dur):
        k = motion._natural_factor(e, nw, nh) * motion.RENDER_SCALE
        d = e.get('depth', 1)
        return max(k * motion.val(e.get('scale'), t, 1) * (1 + (z - 1) * d)
                   for t, z in ((dur * i / 40, motion.val(sc['camera']['zoom'], dur * i / 40, 1)) for i in range(41)))

    def test_the_camera_never_shows_a_photo_bigger_than_its_pixels_allow(self):
        for nw, nh in ((1500, 1721), (1100, 1300), (2400, 3000), (4000, 4500)):
            sc = art.scene_visual('product_macro', {'asset': 'w', 'desc': 'd'}, 'tk-bone', 7.0, seed='m')
            motion.direct(sc, 7.0, 'm', words=WORDS, shots=[{'on': 'دينار', 'to': 'close'}], pixels={'w': (nw, nh)})
            img = next(e for e in sc['elements'] if e['type'] == 'image')
            self.assertLessEqual(self._shown(sc, img, nw, nh, 7.0), motion.SOFT + 1e-3, (nw, nh, sc['camera'].get('cap')))
        small = art.scene_visual('product_macro', {'asset': 'w', 'desc': 'd'}, 'tk-bone', 7.0, seed='m')
        motion.direct(small, 7.0, 'm', words=WORDS, pixels={'w': (1500, 1721)})
        self.assertLess(small['camera']['cap'], 1.4)
        self.assertGreater(max(_zooms(small, 7.0)) - min(_zooms(small, 7.0)), .1)    # the sizes stay apart under the cap
        big = art.scene_visual('archive_photo', {'asset': 'w', 'desc': 'd', 'aspect': 1.3, 'w': 600}, 'tk-bone', 7.0, seed='m')
        motion.direct(big, 7.0, 'm', words=WORDS, pixels={'w': (3000, 2300)})
        self.assertNotIn('cap', big['camera'])                                       # a large scan as a print: the full range

    def test_a_photo_too_small_for_any_shot_is_flagged_by_the_stage_law(self):
        sc = art.scene_visual('product_macro', {'asset': 'w', 'desc': 'd'}, 'tk-bone', 6.0, seed='m')
        motion.direct(sc, 6.0, 'm', words=WORDS, pixels={'w': (700, 800)})
        self.assertLess(sc['camera']['cap'], motion.FLOOR)                           # never upscaled further to make a move:
        self.assertLessEqual(max(_zooms(sc, 6.0)), sc['camera']['cap'] + 1e-6)       # the photo's pixels win, and it is flagged
        found = motion.stage_law({'scenes': [{**sc, 'dur': 6.0}]})
        floor = [f for f in found if f['code'] == 'CAMERA_FLOOR']
        self.assertTrue(floor and "photo's resolution" in floor[0]['say'])

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_the_engine_soft_check_agrees(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); (d / 'assets').mkdir()
            Image.fromarray((np.random.default_rng(2).random((1300, 1100, 3)) * 255).astype('uint8')).save(d / 'assets' / 'w.png')
            capped = art.scene_visual('archive_photo', {'asset': 'w', 'desc': 'd', 'aspect': 1100 / 1300, 'print': True, 'w': 600}, 'tk-bone', 4.0, seed='s')
            motion.direct(capped, 4.0, 's', shots=[{'at': .2, 'to': 'close'}], pixels=motion.pixels(d / 'assets'))
            wild = art.scene_visual('archive_photo', {'asset': 'w', 'desc': 'd', 'aspect': 1100 / 1300, 'print': True, 'w': 600}, 'tk-bone', 4.0, seed='s')
            wild['camera'] = {'zoom': [[0, 1.9], [4.0, 1.9]], 'x': [[0, 360]], 'y': [[0, 640]], 'shots': [], 'clamp': True}
            for sc in (capped, wild): sc.update(dur=4.0, banner=None, transition='cut')
            soft = lambda sc: [l for l in engine.check({'width': 720, 'height': 1280, 'fps': 30, 'scenes': [sc]}, d) if 'look soft' in l]
            self.assertEqual(soft(capped), [])
            self.assertTrue(soft(wild))


class TestCuts(unittest.TestCase):
    def _film(self):
        lines = [{'id': 'a', 'template': 'archive_photo', 'set': 'workshop'}, {'id': 'b', 'template': 'paper_cutout', 'set': 'workshop'},
                 {'id': 'c', 'template': 'kinetic_type', 'set': 'workshop'}, {'id': 'd', 'template': 'kinetic_type', 'set': 'jura'},
                 {'id': 'e', 'template': 'kinetic_type', 'set': 'florence'}, {'id': 'f', 'template': 'city_zoom', 'set': None}]
        params = {'archive_photo': {'asset': 'p', 'desc': 'd', 'aspect': 1.3}, 'paper_cutout': {'asset': 'h', 'aspect': .5, 'person': True},
                  'kinetic_type': {'lines': [{'text': 'كلمات', 'size': 80}]}, 'city_zoom': {'city': 'paris'}}
        scenes, cuts = [], []
        for ln in lines:
            sc = sets.dress(art.scene_visual(ln['template'], params[ln['template']], 'tk-bone', 5.0, seed=ln['id']), ln['set'], 5.0, template=ln['template'])
            motion.direct(sc, 5.0, ln['id'], template=ln['template'])
            cut = quickfilm.cut_for(ln, scenes[-1] if scenes else None, sc, ln['set'], ln['template'], scenes[-1]['transition'] if scenes else None)
            sc.update(id=ln['id'], dur=5.0, transition=cut); scenes.append(sc); cuts.append(cut)
        return scenes, cuts

    def test_the_camera_carries_the_cuts_and_a_line_can_ask_for_its_own(self):
        scenes, cuts = self._film()
        self.assertEqual(cuts, ['cut', 'match', 'through', 'whip', 'through', 'cut'])   # pictures match, one place pushes on,
        self.assertNotIn('fade', cuts); self.assertNotIn('slide', cuts)              # new worlds whip or push in turn
        for asked, want in (('push', 'through'), ('match', 'match'), ('whip', 'whip'), ('fade', 'fade'), ('cut', 'cut')):
            self.assertEqual(quickfilm.cut_for({'id': 'x', 'cut': asked}, scenes[0], scenes[1], 'workshop', 'kinetic_type', None), want)
        with self.assertRaises(ValueError):
            quickfilm.cut_for({'id': 'x', 'cut': 'spin'}, scenes[0], scenes[1], None, 'kinetic_type', None)
        quickfilm.cross(scenes)
        b = scenes[1]
        self.assertIn('matched', b['camera'])                                        # b's subject starts where a's was
        sx, sy, _ = motion.screen_point(b, 0, *b['camera']['start']['focus'])
        self.assertAlmostEqual(sx, b['camera']['matched'][0], delta=40); self.assertAlmostEqual(sy, b['camera']['matched'][1], delta=40)
        self.assertEqual(len(scenes[2]['cutFocus']), 2)
        self.assertTrue(any(c['name'] == 'whoosh' for c in scenes[2]['sfx']))         # the whip into d is heard

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_cut_types_render(self):
        bar = lambda x, color: {'type': 'svg', 'w': 60, 'h': 1280, 'x': x, 'y': 640, 'still': True, 'noBlur': True,
                                'svg': f'<svg xmlns="http://www.w3.org/2000/svg" width="60" height="1280"><rect width="60" height="1280" fill="{color}"/></svg>'}
        sq = {'type': 'svg', 'w': 100, 'h': 100, 'x': 360, 'y': 640, 'still': True,
              'svg': '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#ffffff"/></svg>'}
        sc = lambda tr, theme, els, **kw: {'dur': 2.0, 'theme': theme, 'floor': False, 'transition': tr, 'elements': els, **kw}
        sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', 'style': {'grain': 0, 'vignette': 0}, 'scenes': [
            sc('cut', 'rust', [bar(360, '#ffffff')]),
            sc('whip', 'navy', []),                                                  # 2.0: a whip pan
            sc('through', 'sage', [sq], cutFocus=[360, 640]),                        # 4.0: push-through
            sc('match', 'plum', [])]}                                                # 6.0: match dissolve
        with tempfile.TemporaryDirectory() as d:
            from PIL import Image
            times = [2.16, 3.0, 3.85, 4.03, 4.95, 6.25, 5.9, 6.7]
            f = [np.asarray(Image.open(p).convert('RGB'), dtype=float) for p in engine.stills(sb, Path(d), times, scale=.5)]
            rust, navy = np.array([0xC5, 0x62, 0x2E]), np.array([0x1F, 0x2C, 0x55])
            mid = f[0]
            near = lambda px, c: np.abs(px - c).mean() < 45
            self.assertTrue(near(mid[320, 40:140].mean(0), navy))            # rtl: the new page comes in from the left,
            self.assertTrue(near(mid[320, 220:340].mean(0), rust))           # the old one sweeps out to the right
            edge = np.abs(np.diff(mid[320, 180:360].mean(1)))                # the white bar, smeared sideways
            sharp = np.abs(np.diff(f[1][320, :].mean(1)))
            self.assertLess(edge.max(), 60); self.assertLess(edge.max(), .5 * max(sharp.max(), 120))
            white = lambda im: int((im[:, :, :].min(2) > 200).sum(1).max())  # widest white run in a row (px at scale .5)
            self.assertGreater(white(f[3]), 1.25 * white(f[4]))               # born too close, then settled at 100 px
            self.assertAlmostEqual(white(f[4]), 50, delta=4)
            mean = lambda im: im[40:200, 40:300].reshape(-1, 3).mean(0)
            before, mid, after = mean(f[6]), mean(f[5]), mean(f[7])
            span = np.abs(after - before).sum()
            self.assertGreater(span, 60)
            self.assertGreater(np.abs(mid - before).sum(), .25 * span)      # half way through the dissolve
            self.assertGreater(np.abs(mid - after).sum(), .25 * span)


class TestMotionBlur(unittest.TestCase):
    def test_glides_are_asymmetric_and_words_leave_before_the_cut(self):
        sc = art.scene_visual('kinetic_type', {'lines': [{'text': 'كلمات', 'size': 80}, {'text': 'أخرى', 'size': 60, 'at': .6}]}, 'tk-bone', 5.0)
        motion.choreograph(sc, 5.0, leaving=True)
        words = [e for e in sc['elements'] if e['type'] == 'text']
        self.assertTrue(all(e['in']['type'] == 'flyU' and e['in']['dur'] >= .85 for e in words))
        self.assertTrue(all(e['out']['type'] == 'flyR' and e['out']['dur'] < .5 for e in words))     # in slowly, out fast
        self.assertNotEqual(words[0]['out']['at'], words[1]['out']['at'])                             # one after another
        self.assertTrue(all(e['out']['at'] < 5.0 - .3 for e in words))
        last = art.scene_visual('kinetic_type', {'lines': [{'text': 'كلمات', 'size': 80}]}, 'tk-bone', 5.0)
        motion.choreograph(last, 5.0, leaving=False)
        self.assertNotIn('out', last['elements'][0])

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_a_fast_move_is_blurred_along_its_travel_and_a_resting_one_is_sharp(self):
        from PIL import Image
        box = {'type': 'svg', 'w': 120, 'h': 300, 'x': 360, 'y': 640, 'still': True, 'in': {'type': 'flyL', 'at': 0.2, 'from': 500},
               'svg': '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="300"><rect width="120" height="300" fill="#ffffff"/></svg>'}
        sb = lambda blur: {'width': 720, 'height': 1280, 'fps': 30, 'motionBlur': blur, 'style': {'grain': 0, 'vignette': 0},
                           'scenes': [{'dur': 3.0, 'theme': 'navy', 'floor': False, 'elements': [box]}]}
        with tempfile.TemporaryDirectory() as d:
            imgs = {}
            for blur in (True, False):
                fs = engine.stills(sb(blur), Path(d) / str(blur), [0.52, 2.5], scale=.5)
                imgs[blur] = [np.asarray(Image.open(p).convert('L'), dtype=float) for p in fs]
            ramp = lambda im: int(((im[320] > 60) & (im[320] < 200)).sum())    # pixels part way between the box and the page
            vramp = lambda im: int(((im[:, im.shape[1] // 2] > 60) & (im[:, im.shape[1] // 2] < 200)).sum())
            self.assertGreater(ramp(imgs[True][0]), ramp(imgs[False][0]) + 15)  # a sideways smear while it flies in
            self.assertLess(vramp(imgs[True][0]), 12)                           # along its travel only
            self.assertLessEqual(abs(ramp(imgs[True][1]) - ramp(imgs[False][1])), 2)  # at rest: no filter at all


class TestStageLaw(unittest.TestCase):
    def test_few_movers_a_camera_under_the_floor_and_a_fade_in_one_place_are_flagged(self):
        bare = {'id': 'a', 'dur': 5.0, 'elements': [{'type': 'text', 'text': 'x', 'in': {'type': 'rise'}}],
                'camera': {'zoom': [[0, 1.0], [5.0, 1.04]], 'x': [[0, 360]], 'y': [[0, 640]]}, 'set': 'workshop', 'transition': 'cut'}
        world = sets.dress(art.scene_visual('kinetic_type', {'lines': [{'text': 'كلمات'}]}, 'tk-bone', 5.0), 'workshop', 5.0)
        motion.direct(world, 5.0, 'b')
        world.update(id='b', dur=5.0, transition='fade')
        moved = {**world, 'id': 'c', 'transition': 'through'}
        card = {'dur': 3.0, 'endcard': 'timekeeper', 'elements': []}
        found = motion.stage_law({'scenes': [bare, world, moved, card]})
        self.assertEqual([(f['code'], f['scene']) for f in found], [('FEW_MOVERS', 0), ('CAMERA_FLOOR', 0), ('FADE_SAME_PLACE', 1)])
        self.assertGreaterEqual(sum(map(motion.moving, world['elements'])), motion.MOVERS)
        lines = quality.stage({'scenes': [bare, world, moved, card]})
        self.assertTrue(lines[0].startswith('scene 1  0.0-5.0s  only 1 things move'))
        self.assertIn('zoom 1.04', lines[1]); self.assertIn('same place (workshop)', lines[2])
        self.assertEqual(quality.stage({'scenes': [{**world, 'transition': 'cut'}]}), [])
        own = {'dur': 5.0, 'elements': [], 'camera': {'own': 'city_zoom', 'zoom': [[0, 1.0]]}}
        self.assertFalse([f for f in motion.stage_law({'scenes': [own]}) if f['code'] == 'CAMERA_FLOOR'])

    def test_the_review_reads_the_stage_law(self):
        src = (Path(motion.__file__).parent / 'review.py').read_text(encoding='utf-8')
        for code in ('STAGE_FEW_MOVERS', 'CAMERA_UNDER_FLOOR', 'FADE_SAME_PLACE'):
            self.assertIn(code, src)
        self.assertIn('motion.stage_law(esb)', src)


if __name__ == '__main__':
    unittest.main()
