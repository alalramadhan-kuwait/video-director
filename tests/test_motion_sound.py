"""Étienne's review of Halter, made into rules the engine keeps: real pictures never tremble, every camera moves at
least 3 %, the new story sounds exist and are made the same every time, at most 15 effects a minute, beds start before
their cut, a map journey can be a train, the end card is clean, and a film file can ask for its own sounds."""
from tests import _guard  # noqa: F401
import hashlib, json, re, shutil, subprocess, sys, tempfile, unittest, wave
from pathlib import Path

import numpy as np
import yaml

from director import quality, quickfilm
from director.studio import art, engine, mix, motion, storyboard

HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()
SFX = engine.ENGINE / 'assets/sfx'
NEW = ('train', 'train_bed', 'train_horn', 'gavel', 'tower_strike', 'footsteps', 'thud', 'tick_slow')


def _wav(path: Path, x: np.ndarray, sr=44100):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


def _read(path: Path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), '<i2') / 32768, w.getframerate()


class TestNoTremble(unittest.TestCase):
    def test_photos_and_cutouts_never_boil_and_people_breathe(self):
        for tech, p in (('product_macro', {'asset': 'w', 'desc': 'd'}), ('archive_photo', {'asset': 'w', 'desc': 'd', 'aspect': 1.4}),
                        ('archive_photo', {'asset': 'w', 'desc': 'd', 'aspect': .7}), ('product_reveal', {'asset': 'w', 'desc': 'd', 'name': 'n'})):
            sc = art.scene_visual(tech, p, 'tk-bone', 5.0)
            pics = [e for e in sc['elements'] if e['type'] in art.STEADY]
            self.assertTrue(pics and all(e.get('noBoil') for e in pics), tech)
        person = art.scene_visual('paper_cutout', {'asset': 'h', 'person': True, 'aspect': .5}, 'tk-bone', 6.0)
        cut = next(e for e in person['elements'] if e['type'] == 'cutout')
        self.assertTrue(cut['noBoil']); self.assertEqual(cut['idle']['type'], 'breathe')
        watch = art.scene_visual('paper_cutout', {'asset': 'w', 'aspect': 1.0}, 'tk-bone', 6.0)
        self.assertNotIn('idle', next(e for e in watch['elements'] if e['type'] == 'cutout'))     # a watch rests
        drawn = art.scene_visual('paper_cutout', {'drawn': {'kind': 'scientist'}}, 'tk-bone', 6.0)
        fig = next(e for e in drawn['elements'] if e['type'] == 'svg' and e.get('idle'))
        self.assertTrue(fig['noBoil']); self.assertEqual(fig['idle']['type'], 'breathe')
        sc = art.backdrop(art.scene_visual('stat_counter', {'value': 5}, 'tk-ink', 5.0), 'p', 5.0)
        self.assertTrue(sc['elements'][0]['noBoil'])

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_the_engine_holds_a_photo_still_while_the_paper_boils(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            Image.fromarray((np.random.default_rng(1).random((300, 300, 3)) * 255).astype('uint8')).save(d / 'p.png')
            sb = {'width': 720, 'height': 1280, 'fps': 30, 'scenes': [{'dur': 3, 'floor': False, 'theme': 'cream', 'elements': [
                {'type': 'image', 'src': 'p.png', 'w': 300, 'h': 300, 'x': 360, 'y': 400, 'frame': False},
                {'type': 'text', 'text': 'PAPER', 'size': 90, 'x': 360, 'y': 800, 'color': '#111'}]}]}
            a, b = engine.stills(sb, d, [1.00, 1.09], scale=1)            # two different boil frames (12 a second)
            A, B = (np.asarray(Image.open(f).convert('L'), dtype=np.int16) for f in (a, b))
            self.assertEqual(int(np.abs(A[280:520, 240:480] - B[280:520, 240:480]).max()), 0)   # the photo: not one pixel moves
            self.assertGreater(int(np.abs(A[740:860, 150:570] - B[740:860, 150:570]).max()), 40)   # the paper words still boil


class TestCamera(unittest.TestCase):
    def test_every_template_moves_the_camera_at_least_three_percent(self):
        for t in art.catalogue():
            if t['id'] not in art.BUILDERS or t['status'] != 'implemented': continue
            for dur in (2.5, 4.5, 7.0, 12.0):
                sc = art.scene_visual(t['id'], t['example'], t.get('theme', 'tk-bone'), dur, seed=f"{t['id']}{dur}")
                self.assertGreaterEqual(motion.amount(sc, dur) + motion.TOL, motion.MIN, (t['id'], dur, sc.get('camera')))
                for k in ('zoom', 'x', 'y'):                                  # still moving at the cut, not eased to a stop
                    keys = (sc['camera'].get(k) or [])
                    if len(keys) >= 2 and keys[-1][1] != keys[-2][1]:
                        self.assertNotIn(keys[-1][2] if len(keys[-1]) > 2 else 'inOutCubic', ('inOutCubic', 'outCubic'), (t['id'], k))

    def test_moves_are_seeded_and_varied_and_never_show_the_frame_edge(self):
        a = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .6}, 'tk-bone', 6.0, seed='l3')
        b = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .6}, 'tk-bone', 6.0, seed='l3')
        self.assertEqual(a['camera'], b['camera'])
        kinds = {motion.move(6.0, f'l{i}')['move'] for i in range(12)}
        self.assertGreaterEqual(len(kinds), 3)
        for i in range(40):
            for dur in (3.0, 9.0):
                cam = motion.move(dur, i)
                self.assertTrue(motion.MIN <= motion.amount({'camera': cam}, dur) <= 0.06, cam)
                for j in range(31):                                           # a full-frame picture covers the frame all along
                    t = dur * j / 30
                    z, x, y = (motion.val(cam.get(k), t, c) for k, c in (('zoom', 1), ('x', 360), ('y', 640)))
                    self.assertLessEqual(360 - x * z, 0.5); self.assertGreaterEqual(360 + (720 - x) * z, 719.5)
                    self.assertLessEqual(640 - y * z, 0.5); self.assertGreaterEqual(640 + (1280 - y) * z, 1279.5)

    def test_a_long_scene_punches_in_on_a_word(self):
        sc = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .6}, 'tk-bone', 9.0, seed='l5')
        before = motion.amount(sc, 9.0)
        at = motion.word_punch(sc, [[0.3, 'في'], [4.1, 'Antiqua'], [5.0, '1998'], [8.5, 'نهاية']], 9.0, 'l5')
        self.assertEqual(at, 5.0)                                            # the number, said mid-scene
        self.assertGreater(motion.amount(sc, 9.0), before)
        z = lambda t: motion.val(sc['camera']['zoom'], t, 1)
        self.assertGreater(z(5.45) - z(4.95), 0.015)                         # the punch: 2.5 % in under half a second
        short = art.scene_visual('paper_cutout', {'asset': 'h', 'aspect': .6}, 'tk-bone', 4.0, seed='l6')
        self.assertIsNone(motion.word_punch(short, [[2.0, 'x']], 4.0, 'l6'))

    def test_the_quality_step_and_the_review_flag_a_camera_that_barely_moves(self):
        still = {'id': 'l1', 'dur': 10.0, 'camera': {'zoom': [[0, 1.0], [10.0, 1.02]], 'x': [[0, 360]], 'y': [[0, 640]]}, 'elements': []}
        moving = {'id': 'l2', 'dur': 5.0, 'camera': motion.move(5.0, 'l2'), 'elements': []}
        card = {'dur': 3.0, 'endcard': 'timekeeper', 'elements': []}
        out = quality.camera({'scenes': [moving, still, card]})
        self.assertEqual(len(out), 1); self.assertTrue(out[0].startswith('scene 2  5.0-15.0s  the camera moves 2.0 %'))
        self.assertEqual(quality.camera({'scenes': [{'dur': 4, 'elements': []}]})[0][:7], 'scene 1')   # no camera at all


class TestSounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run1 = subprocess.run([sys.executable, str(engine.ENGINE / 'scripts/make-sfx.py')], capture_output=True, text=True)
        cls.hash1 = {n: hashlib.sha256((SFX / f'{n}.wav').read_bytes()).hexdigest() for n in NEW + ('tick', 'stamp', 'crowd')}

    def test_the_new_sounds_exist_and_are_the_same_every_time(self):
        self.assertEqual(self.run1.returncode, 0, self.run1.stderr)
        subprocess.run([sys.executable, str(engine.ENGINE / 'scripts/make-sfx.py')], check=True, capture_output=True)
        again = {n: hashlib.sha256((SFX / f'{n}.wav').read_bytes()).hexdigest() for n in self.hash1}
        self.assertEqual(again, self.hash1)
        kit = (engine.ENGINE / 'scripts/make-sfx.py').read_text()
        for n in NEW:
            self.assertIn(f"save('{n}'", kit)

    def test_each_sound_is_what_it_says(self):
        def secs(n):
            x, sr = _read(SFX / f'{n}.wav'); return x, sr, len(x) / sr
        x, sr, d = secs('train')
        self.assertAlmostEqual(d, 6.0, delta=.5)
        rms = [np.sqrt(np.mean(x[i:i + sr // 2] ** 2)) for i in range(0, len(x) - sr // 2, sr // 2)]
        k = int(np.argmax(rms)); self.assertTrue(2 <= k <= len(rms) - 3)      # it swells and fades: loudest as it passes
        self.assertGreater(rms[k], 8 * rms[0]); self.assertGreater(rms[k], 8 * rms[-1])
        x, sr, d = secs('tower_strike'); self.assertGreater(d, 6)               # a long decay
        tail = np.sqrt(np.mean(x[int(4 * sr):int(5 * sr)] ** 2)); self.assertGreater(tail, 0.01)
        x, sr, d = secs('tick_slow')
        env = np.abs(x)
        hits = [i / sr for i in range(1, len(env)) if env[i] > .2 and env[i - 1] <= .2]
        onsets = [t for i, t in enumerate(hits) if i == 0 or t - hits[i - 1] > .08]
        gaps = np.diff(onsets)
        self.assertGreaterEqual(len(onsets), 6)
        self.assertTrue(all(b > a for a, b in zip(gaps, gaps[1:])), gaps)    # each tick later than the last: it slows
        self.assertLess(onsets[-1], 3.2)                                      # and stops
        x, sr, d = secs('footsteps')
        e = np.array([np.sqrt(np.mean(x[i:i + 441] ** 2)) for i in range(0, len(x) - 441, 441)])
        peaks = [i for i in range(1, len(e) - 1) if e[i] > .15 and e[i] >= e[i - 1] and e[i] >= e[i + 1]]
        steps = [p for i, p in enumerate(peaks) if i == 0 or p - peaks[i - 1] > 20]
        self.assertTrue(4 <= len(steps) <= 6, steps)

    def test_train_is_a_bed_and_a_template_sound(self):
        from director.studio import sets
        self.assertTrue((SFX / 'train_bed.wav').is_file())
        self.assertEqual(mix.sound_file('train', bed=True).name, 'train_bed.wav')
        self.assertEqual(mix.sound_file('train').name, 'train.wav')
        self.assertIn("'_bed.wav'", (engine.ENGINE / 'scripts/render.mjs').read_text())   # the engine loops the bed take too


class TestMix(unittest.TestCase):
    def _film(self, n=30, dur=20.0):
        names = ['paper_place', 'whoosh', 'click', 'stamp', 'pin', 'paper_slide']
        scenes = []
        for s in range(3):
            cues = [{'at': round(.3 + i * (dur - 1) / (n // 3), 2), 'name': names[(i + s) % len(names)], 'gain': -12} for i in range(n // 3)]
            scenes.append({'id': f'l{s}', 'dur': dur, 'transition': 'cut', 'banner': None, 'sfx': cues})
        return scenes

    def test_at_most_fifteen_effects_a_minute_the_least_important_go_first(self):
        scenes = self._film()
        scenes[1]['sfx'].append({'at': 5.0, 'name': 'gavel', 'gain': -8, 'owner': True, 'fixed': True})
        end = {'dur': 3.0, 'endcard': 'timekeeper', 'sfx': [{'at': .2, 'name': 'tick', 'gain': -12}, {'at': 1.8, 'name': 'tick_pair', 'gain': -8}]}
        r = mix.apply(scenes + [end], {})
        kept = [c for s in scenes for c in s['sfx']]
        self.assertLessEqual(len(kept), 15)                                  # 60 s of story: 15 at most
        self.assertTrue(any(c['name'] == 'gavel' for c in kept))             # the film file's own cue stays
        self.assertEqual(len(end['sfx']), 2)                                 # the end card's ticks stay, uncounted
        self.assertTrue(r['dropped'])
        first = {d['name'] for d in r['dropped'][:8]}
        self.assertLessEqual(first, {'paper_place', 'paper_slide', 'whoosh'})  # paper and whooshes go first
        self.assertFalse(any('owner' in c or 'fixed' in c for c in kept))     # no bookkeeping left in the storyboard
        # any 60 s window, not just the average
        t = sorted(i * 20 + c['at'] for i, s in enumerate(scenes) for c in s['sfx'])
        self.assertTrue(all(sum(1 for u in t if a <= u < a + 60) <= 15 for a in t))

    def test_paper_sounds_only_when_paper_comes_in(self):
        sc = [{'id': 'a', 'dur': 4, 'transition': 'cut', 'banner': None, 'sfx': []},
              {'id': 'b', 'dur': 4, 'transition': 'slide', 'banner': 'عنوان', 'sfx': [{'at': .35, 'name': 'paper_place', 'gain': -12},
                                                                                     {'at': .6, 'name': 'paper_place', 'gain': -12},
                                                                                     {'at': 2.0, 'name': 'paper_place', 'gain': -12}]},
              {'id': 'c', 'dur': 4, 'transition': 'fade', 'banner': None, 'sfx': []}]
        mix.paper_cues(sc)
        self.assertEqual(sc[0]['sfx'], [])                                   # no banner, a cut: no paper sound
        self.assertEqual(sc[2]['sfx'], [])                                   # a fade is not paper moving
        names = [(c['at'], c['name']) for c in sc[1]['sfx']]
        self.assertEqual(names, [(0.0, 'paper_slide'), (2.0, 'paper_place')])  # one slide, then nothing within 0.8 s, at most 2

    def test_beds_start_half_a_second_before_their_cut(self):
        sc = [{'id': 'a', 'dur': 4, 'beds': [{'name': 'room', 'gain': -30}]},
              {'id': 'b', 'dur': 4, 'beds': [{'name': 'room', 'gain': -30}, {'name': 'wind', 'gain': -28}]},
              {'id': 'c', 'dur': 4, 'beds': [{'name': 'train', 'gain': -26}, {'name': 'crowd', 'from': 1.0, 'gain': -30}]}]
        mix.jcut(sc)
        self.assertNotIn('lead', sc[0]['beds'][0])                           # the film's first scene starts at 0
        self.assertNotIn('lead', sc[1]['beds'][0])                           # the same room carries on across the cut
        self.assertEqual(sc[1]['beds'][1]['lead'], mix.LEAD)
        self.assertEqual(sc[2]['beds'][0]['lead'], .5)
        self.assertNotIn('lead', sc[2]['beds'][1])                           # a bed that comes in later is not a J-cut

    def test_beds_and_effects_are_levelled_against_the_voice(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            t = np.arange(44100 * 2) / 44100
            _wav(d / 'v.wav', .3 * np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 2 * t) > -.5))
            v = mix.level(str(d / 'v.wav'))
            sc = [{'id': 'a', 'dur': 4, 'beds': [{'name': 'room', 'gain': -34}, {'name': 'watch_run', 'gain': -28}],
                   'sfx': [{'at': 1, 'name': 'stamp', 'gain': -9}, {'at': 2, 'name': 'paper_place', 'gain': -14}]}]
            mix.levels(sc, {0: v})
            main = sc[0]['beds'][1]
            under = v - (mix.level(str(mix.sound_file('watch_run', True))) + main['gain'])
            self.assertAlmostEqual(under, mix.TICK_UNDER, delta=.2)            # a running movement: 36 dB under the voice
            second = v - (mix.level(str(mix.sound_file('room', True))) + sc[0]['beds'][0]['gain'])
            self.assertAlmostEqual(second - under, 6, delta=.2)               # the second keeps its distance below
            for c in sc[0]['sfx']:
                shot = v + 3 - (mix.level(str(mix.sound_file(c['name'])), 'peak') + c['gain'])
                self.assertTrue(3 <= shot <= 6, (c, shot))                    # one-shots 3-6 dB under the voice

    def _voice(self, d):
        t = np.arange(44100 * 2) / 44100
        _wav(d / 'v.wav', .3 * np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 2 * t) > -.5))
        return mix.level(str(d / 'v.wav'))

    def _under(self, v, b):
        return v - (mix.level(str(mix.sound_file(b['name'], True))) + b['gain'])

    def test_beds_are_felt_not_heard(self):
        """The owner on v10: «الاصوات اللي بالخلفية مزعجة جدا». One bed 34 dB under the voice while it sets the place,
        then 40 under; a tick or a tock 36 at most; a second bed 6 dB further down; never a third."""
        with tempfile.TemporaryDirectory() as d:
            v = self._voice(Path(d))
        sc = [{'id': 'a', 'dur': 6, 'beds': [{'name': 'room', 'gain': -30}, {'name': 'crowd', 'gain': -38}, {'name': 'drone', 'gain': -42}]},
              {'id': 'b', 'dur': 6, 'beds': [{'name': 'tock', 'gain': -26}]},
              {'id': 'c', 'dur': 6, 'beds': [{'name': 'tick', 'gain': -4, 'fixed': True}]},
              {'id': 'd', 'dur': 6, 'beds': [{'name': 'tock', 'gain': -60, 'fixed': True}]}]
        mix.jcut(sc); mix.levels(sc, {i: v for i in range(4)}); mix.settle(sc)
        self.assertEqual([b['name'] for b in sc[0]['beds']], ['room', 'crowd'])            # never a third
        main, second = sc[0]['beds']
        self.assertAlmostEqual(self._under(v, main), mix.BED_AIM, delta=.2)
        self.assertGreaterEqual(self._under(v, second) - self._under(v, main), mix.BED_SECOND - .1)
        self.assertEqual(main['settle']['at'], mix.BED_HEAD)                               # the film's first scene: no lead
        self.assertAlmostEqual(main['gain'] - main['settle']['gain'], mix.BED_SETTLE - mix.BED_AIM, delta=.11)
        tock = sc[1]['beds'][0]
        self.assertAlmostEqual(self._under(v, tock), mix.TICK_UNDER, delta=.2)              # no repetitive tick under speech
        self.assertEqual(tock['settle']['at'], mix.LEAD + mix.BED_HEAD)                     # the J-cut, then 1.5 s of the scene
        self.assertAlmostEqual(self._under(v, sc[2]['beds'][0]), mix.TICK_UNDER, delta=.2)  # a film's own gain, capped
        self.assertEqual(sc[3]['beds'][0]['gain'], -60)                                     # a quieter one is kept as it is
        for s_ in sc:
            for b in s_['beds']:
                self.assertGreaterEqual(self._under(v, b), 34 - .2, b)

    def test_a_bed_that_carries_on_does_not_swell_and_the_film_can_turn_beds_down(self):
        with tempfile.TemporaryDirectory() as d:
            v = self._voice(Path(d))
        mk = lambda: [{'id': 'a', 'dur': 4, 'beds': [{'name': 'room', 'gain': -30}]}, {'id': 'b', 'dur': 4, 'beds': [{'name': 'room', 'gain': -30}]}]
        a, b = mk(), mk()
        mix.apply(a, {0: v, 1: v}); mix.apply(b, {0: v, 1: v}, bed_gain=-5)
        self.assertIn('settle', a[0]['beds'][0])
        self.assertNotIn('settle', a[1]['beds'][0])                                          # the same room: it stays low
        self.assertAlmostEqual(a[1]['beds'][0]['gain'], a[0]['beds'][0]['settle']['gain'], delta=.01)
        self.assertAlmostEqual(a[0]['beds'][0]['gain'] - b[0]['beds'][0]['gain'], 5, delta=.01)
        self.assertAlmostEqual(a[0]['beds'][0]['settle']['gain'] - b[0]['beds'][0]['settle']['gain'], 5, delta=.01)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg not available')
    def test_the_music_is_levelled_against_the_voice(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            t = np.arange(44100 * 3) / 44100
            _wav(d / 'm.wav', .1 * np.sin(2 * np.pi * 330 * t))
            lv = mix.level(str(d / 'm.wav'))
            g = mix.music_gain({0: -25.0, 1: -24.0, 2: -26.0}, d / 'm.wav', -6.0)
            self.assertAlmostEqual(lv + g, -25.0 - mix.MUSIC_UNDER, delta=.3)        # MUSIC_UNDER under the voice in the pauses
            self.assertEqual(mix.music_gain({0: 0.0}, d / 'm.wav', -6.0), -6.0)        # never above the brand's gain
            self.assertEqual(mix.music_gain({}, d / 'm.wav', -6.0), -6.0)              # no voice: the brand's gain

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_the_engine_settles_a_bed_after_it_sets_the_place(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            bed = {'name': 'room', 'gain': -6, 'settle': {'at': 1.0, 'gain': -18, 'ramp': .5}}
            sb = {'width': 180, 'height': 320, 'fps': 5, 'audio': {'autoSfx': False}, 'scenes': [{'dur': 4.0, 'floor': False, 'elements': [], 'beds': [bed]}]}
            (d / 'b.json').write_text(json.dumps(sb))
            engine.run(d / 'b.json', '-o', d / 'b.mp4', '--scale', 1)
            lv = []
            for a, b in ((.5, .95), (2.5, 3.4)):
                r = subprocess.run(['ffmpeg', '-v', 'info', '-ss', str(a), '-to', str(b), '-i', str(d / 'b.mp4'), '-vn', '-af', 'volumedetect',
                                    '-f', 'null', '-'], capture_output=True, text=True)
                lv.append(float(re.search(r'mean_volume: (-?[\d.]+)', r.stderr).group(1)))
        self.assertAlmostEqual(lv[0] - lv[1], 12, delta=2.5)                                # it sets the place, then sits 12 dB lower

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_the_engine_starts_a_bed_before_its_cut(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            lv = {}
            for name, lead in (('jcut', .5), ('hard', 0)):
                bed = {'name': 'train', 'gain': -6, **({'lead': lead} if lead else {})}
                sb = {'width': 180, 'height': 320, 'fps': 5, 'audio': {'autoSfx': False},
                      'scenes': [{'dur': 2.0, 'floor': False, 'elements': []}, {'dur': 2.0, 'floor': False, 'elements': [], 'beds': [bed]}]}
                (d / f'{name}.json').write_text(json.dumps(sb))
                engine.run(d / f'{name}.json', '-o', d / f'{name}.mp4', '--scale', 1)
                r = subprocess.run(['ffmpeg', '-v', 'info', '-ss', '1.55', '-to', '1.95', '-i', str(d / f'{name}.mp4'), '-vn', '-af', 'volumedetect',
                                    '-f', 'null', '-'], capture_output=True, text=True)
                m = re.search(r'mean_volume: (-?[\d.]+)', r.stderr)
                lv[name] = float(m.group(1)) if m else -91.0
            self.assertGreater(lv['jcut'], lv['hard'] + 20)                  # heard before the picture changes


class TestMapTrain(unittest.TestCase):
    P = {'view': {'lon': 4.5, 'lat': 47.5, 'span': 9}, 'marker': 'train',
         'pins': [{'id': 'p', 'lon': 2.35, 'lat': 48.85, 'label': 'Paris', 'at': .2}, {'id': 's', 'lon': 6.56, 'lat': 46.82, 'label': 'Jura', 'at': .2}],
         'routes': [{'from': 'p', 'to': 's', 'at': .5, 'dur': 3.0, 'trainColor': '#00FF00'}]}

    def test_the_map_template_passes_the_train_marker_and_its_sound(self):
        sc = art.scene_visual('map', self.P, 'tk-bone', 5.0)
        self.assertEqual(sc['elements'][0]['routes'][0]['marker'], 'train')
        self.assertIn({'at': .5, 'name': 'train', 'gain': -10}, sc['sfx'])
        plane = art.scene_visual('map', {**self.P, 'marker': None}, 'tk-bone', 5.0)
        self.assertNotIn('marker', plane['elements'][0]['routes'][0])
        self.assertFalse(any(c['name'] == 'train' for c in plane.get('sfx', [])))

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_a_small_train_runs_along_the_route(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            n = {}
            for kind in ('train', 'plane'):
                p = json.loads(json.dumps(self.P)); p['marker'] = kind if kind == 'train' else None
                sc = {**art.scene_visual('map', p, 'tk-bone', 5.0), 'dur': 5.0}
                f = engine.stills({'width': 720, 'height': 1280, 'fps': 30, **art.style('timekeeper'), 'scenes': [sc]}, d / kind, [2.0], scale=.5)[0]
                px = np.asarray(Image.open(f).convert('RGB')).astype(int)
                n[kind] = int(((px[..., 1] > 200) & (px[..., 0] < 80) & (px[..., 2] < 80)).sum())
            self.assertGreater(n['train'], 60)                                # the train's paint (trainColor), mid-route
            self.assertEqual(n['plane'], 0)


class TestEndCard(unittest.TestCase):
    def test_three_seconds_no_banner_no_black_tail(self):
        with tempfile.TemporaryDirectory() as d:
            cards = storyboard._endcard(Path(d))
        self.assertEqual(len(cards), 1)                                       # no black scene after the card
        card = cards[0]
        self.assertEqual(card['dur'], 3.0); self.assertIsNone(card['banner'])
        black = card['elements'][-1]
        self.assertEqual(black['opacity'][-1], [3.0, 1])                      # the fade ends with the film, not 1.3 s before
        self.assertGreaterEqual(black['opacity'][0][0], 2.5)
        self.assertTrue(all(c['at'] < 2.0 for c in card['sfx']))


class TestFilmFileSounds(unittest.TestCase):
    WORDS = [{'w': 'ثم', 's': .1}, {'w': 'دقّ', 's': .5}, {'w': 'Phillips', 's': 1.2}, {'w': 'دقّ', 's': 2.0}]

    def test_a_line_asks_for_effects_at_words_and_times_and_its_own_bed(self):
        ln = yaml.safe_load('''
id: l0
sfx:
  - {name: gavel, on: Phillips}
  - {name: gavel, on: دقّ, nth: 2, offset: -0.1, gain: -6}
  - {name: train_horn, at: 2.5}
  - {name: thud, on: absent}
  - stamp
bed: train
''')
        self.assertIs(next(iter(ln['sfx'][0].keys() - {'name'})), True)        # YAML 1.1 reads `on` as true: still understood
        sc = {'sfx': [], 'beds': [{'name': 'room', 'gain': -30}]}
        missing = quickfilm.line_sound(sc, ln, self.WORDS, 4.0)
        got = [(c['at'], c['name'], c.get('fixed', False)) for c in sc['sfx']]
        self.assertEqual(got, [(1.35, 'gavel', False), (2.05, 'gavel', True), (2.5, 'train_horn', False), (0.0, 'stamp', False)])
        self.assertTrue(all(c['owner'] for c in sc['sfx']))
        self.assertEqual(len(missing), 1); self.assertIn('absent', missing[0])
        self.assertEqual(sc['beds'], [{'name': 'train', 'gain': -26}])
        silent = {'beds': [{'name': 'room'}]}
        quickfilm.line_sound(silent, {'id': 'x', 'bed': 'none'}, [], 3.0)
        self.assertEqual(silent['beds'], [])
        fixed = {}
        quickfilm.line_sound(fixed, {'id': 'x', 'bed': [{'name': 'wind', 'gain': -30}, 'crowd']}, [], 3.0)
        self.assertEqual(fixed['beds'], [{'gain': -30, 'name': 'wind', 'fixed': True}, {'name': 'crowd', 'gain': -26}])


if __name__ == '__main__':
    unittest.main()
