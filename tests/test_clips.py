"""AI video clips (rule 18l): a clip replaces the scene's picture or plays behind its print; it is slowed to fill its scene
(never below 0.7x), then runs backwards and on again; a watch is never generated; every clip is labelled on screen and
credited; the checks count a clip as motion; the engine renders it frame by frame from the scene time alone."""
from tests import _guard  # noqa: F401
import json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path

import yaml

from director import quality, quickfilm
from director.studio import art, clips, engine, moods, motion, sets

HAVE_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))
HAVE_RENDER = HAVE_FFMPEG and bool(shutil.which('node')) and engine.RENDER.is_file()
INFO = {'seconds': 5.04, 'w': 720, 'h': 1280, 'fps': 24.0}


def _testsrc(f: Path, seconds=2.0, size='720x1280', still=False):
    src = f'color=c=0x445566:size={size}:rate=24:duration={seconds}' if still else f'testsrc=size={size}:rate=24:duration={seconds}'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', src, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(f)], check=True)
    return f


def _scene(template, params, world, dur=6.0, mood=None):
    sc = art.scene_visual(template, params, sets.theme_for(world, 'tk-bone'), dur, banner='معرض Basel · 1998', seed='l5')
    sets.dress(sc, world, dur, seed='l5', template=template)
    moods.dress(sc, mood, dur)
    return sc


class TestTiming(unittest.TestCase):
    def test_a_longer_scene_slows_the_clip_never_below_0_7(self):
        t = clips.timing(5.0, 6.0)
        self.assertAlmostEqual(t['rate'], 5 / 6, places=3); self.assertEqual(t['after'], 'cut')    # slowed to fill it exactly
        t = clips.timing(5.0, 9.0)
        self.assertEqual(t['rate'], 0.7); self.assertEqual(t['after'], 'pingpong')                  # still short: ping-pong
        self.assertAlmostEqual(t['plays'], 5 / .7, places=2)
        t = clips.timing(5.0, 4.5)
        self.assertEqual(t['rate'], 1.0); self.assertEqual(t['after'], 'cut')                       # a longer clip is cut

    def test_ping_pong_runs_backwards_from_the_end_at_the_same_rate(self):
        self.assertAlmostEqual(clips.clip_time(2.0, .8, 5.0), 1.6)
        self.assertAlmostEqual(clips.clip_time(5.0 / .7, .7, 5.0), 5.0)                             # the end of the clip
        self.assertAlmostEqual(clips.clip_time(5.0 / .7 + 1.0, .7, 5.0), 5.0 - .7)                   # one second later, back 0.7 s
        self.assertAlmostEqual(clips.clip_time(10 / .7 + .5, .7, 5.0), .35)                          # and forwards again
        self.assertEqual(clips.clip_time(9.0, .7, 5.0, 'hold'), 5.0)                                 # or held on the last frame
        self.assertEqual(clips.clip_time(-.2, 1.0, 5.0), 0.0)
        js = (engine.ROOT / 'vendor/studio-ext/clip.js').read_text(encoding='utf-8')
        self.assertIn('p <= len ? p : 2 * len - p', js)                                              # the engine plays the same formula
        self.assertIn('PM.settle', js)


class TestStoryboard(unittest.TestCase):
    def test_replace_fills_the_frame_and_keeps_only_the_words_and_cards(self):
        sc = _scene('archive_photo', {'asset': 'boy', 'desc': 'a boy', 'card': 'Vianney Halter طفلًا', 'credit': 'رسم بالذكاء الاصطناعي · من صورة',
                                      'aspect': 1.3}, 'paris_rail', mood='wonder')
        self.assertTrue(any(e.get('world') for e in sc['elements']))
        c = clips.spec({'id': 'l1a', 'clip': {'file': 'x.mp4'}})
        self.assertEqual((c['mode'], c['fit'], c['end'], c['label']), ('replace', 'cover', 'pingpong', clips.LABEL))
        beds = list(sc['beds'])
        clips.apply(sc, c, 'assets/l1a_clip.mp4', 6.0, INFO)
        els = sc['elements']
        v = els[0]
        self.assertEqual((v['type'], v['src'], v['w'], v['h'], v['fit']), ('video', 'assets/l1a_clip.mp4', 720, 1280, 'cover'))
        self.assertAlmostEqual(v['rate'], 5.04 / 6, places=3)
        self.assertFalse(v.get('behind'))
        self.assertFalse(any(e.get('world') for e in els))                                           # the world's decor is gone
        self.assertFalse(any(e['type'] in ('photo', 'image', 'cutout') for e in els))               # and the template's picture
        self.assertTrue(any(e['type'] == 'card' for e in els))                                       # the HUD card stays
        self.assertTrue(any(e.get('mood') for e in els))                                             # the mood's light stays over it
        labels = [e for e in els if e['type'] == 'text' and e.get('y') == art.CREDIT_Y]
        self.assertEqual([e['text'] for e in labels], [clips.LABEL])                                 # the label, not the photo's credit
        self.assertEqual(sc['beds'], beds)                                                           # the world is still heard
        self.assertEqual(sc['banner'], 'معرض Basel · 1998')
        motion.direct(sc, 6.0, 'l1a', pixels={}, template='archive_photo')
        self.assertLessEqual(max(motion.val(sc['camera']['zoom'], i / 10, 1) for i in range(61)), 1.0 + 1e-6)   # 720p at 1080p: no zoom
        self.assertEqual(motion.cap(sc, {}), 1.0)
        self.assertEqual(motion.cap({'elements': [dict(v, px=[1440, 2560])]}, {}), 2.0)              # a 1440p clip may come closer
        sb = {'scenes': [dict(sc, dur=6.0)]}
        self.assertEqual(motion.stage_law(sb), []); self.assertEqual(quality.camera(sb), [])          # a clip counts as motion

    def test_behind_replaces_the_world_and_keeps_the_real_print_on_top(self):
        sc = _scene('archive_photo', {'asset': 'antiqua_7', 'desc': 'Antiqua', 'print': True, 'w': 380, 'y': 520, 'aspect': 1.0,
                                      'credit': 'Vianney Halter Antiqua · Phillips', 'card': 'هذه القطعة من عام 1999'}, 'basel_fair')
        n_world = sum(1 for e in sc['elements'] if e.get('world'))
        self.assertGreater(n_world, 8)
        line = {'id': 'l5', 'params': {'asset': 'antiqua_7'}, 'clip': {'file': 'c.mp4', 'mode': 'behind'}}
        clips.apply(sc, clips.spec(line), 'assets/l5_clip.mp4', 9.0, INFO)
        els = sc['elements']
        self.assertEqual(els[0]['type'], 'video'); self.assertTrue(els[0]['behind']); self.assertEqual(els[0]['depth'], 0)
        self.assertEqual(els[0]['rate'], .7)
        self.assertFalse(any(e.get('world') for e in els))
        photo = next(e for e in els if e['type'] == 'photo')
        self.assertEqual(photo['asset'], 'antiqua_7')                                                # the real watch, over the crowd
        quickfilm.line_reveal(sc, {'id': 'l5', 'reveal': {'on': 'Antiqua'}}, [{'w': 'Antiqua', 's': 3.0}], 9.0)
        self.assertGreater(els.index(sc['elements'][-1]), els.index(photo))                          # the velvet still over the print
        credit = [e['text'] for e in els if e['type'] == 'text' and e.get('y') == art.CREDIT_Y]
        self.assertEqual(credit, ['Vianney Halter Antiqua · Phillips · ' + clips.LABEL])
        motion.direct(sc, 9.0, 'l5', shots=[{'at': 0, 'to': 'wide'}, {'at': 3.0, 'to': 'close'}], pixels={'antiqua_7': (2400, 2400)},
                      template='archive_photo')
        self.assertGreater(max(motion.val(sc['camera']['zoom'], i / 10, 1) for i in range(91)), 1.5)   # the clip never holds the close-up back
        self.assertEqual(clips.problems({'photos': {'antiqua_7': {'watch': 'Antiqua'}}, 'lines': [line]}), [])

    def test_a_watch_is_never_generated(self):
        film = {'photos': {'antiqua_7': {'watch': 'Antiqua'}, 'boy': {'person': 'Vianney Halter'}, 'clock': {'not_a_watch': True}},
                'lines': [{'id': 'a', 'params': {'asset': 'antiqua_7'}, 'clip': {'file': 'c.mp4'}},
                          {'id': 'b', 'params': {'asset': 'boy'}, 'clip': {'file': 'c.mp4'}},
                          {'id': 'c', 'params': {'asset': 'clock'}, 'clip': 'c.mp4'},
                          {'id': 'd', 'photo': 'clock', 'clip': {'file': 'c.mp4', 'mode': 'behind'}}]}
        bad = clips.problems(film)
        self.assertEqual(len(bad), 2, bad)
        self.assertTrue(bad[0].startswith('a: a watch is never generated'))
        self.assertTrue(bad[1].startswith('d: '))
        with self.assertRaises(ValueError):
            clips.spec({'id': 'x', 'clip': {'file': 'c.mp4', 'mode': 'over'}})
        d = Path(tempfile.mkdtemp())
        try:
            f = d / 'f.yaml'
            f.write_text(yaml.safe_dump({'lines': [{'id': 'a', 'text': 'x', 'template': 'archive_photo', 'params': {'asset': 'antiqua_7'},
                                                    'clip': {'file': 'c.mp4'}}], 'photos': {'antiqua_7': {'watch': 'Antiqua'}}},
                                       allow_unicode=True), encoding='utf-8')
            with self.assertRaises(ValueError) as e:
                quickfilm.load(f)
            self.assertIn('never generated', str(e.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    @unittest.skipUnless(HAVE_FFMPEG, 'ffmpeg not available')
    def test_frozen_detection_leaves_a_clip_scene_alone(self):
        d = Path(tempfile.mkdtemp())
        try:
            f = _testsrc(d / 'still.mp4', 2.0, '180x320', still=True)
            self.assertTrue(quality.frozen(f))
            self.assertEqual(quality.frozen(f, moving=[(0.0, 2.0)]), [])
            self.assertEqual(clips.probe(_testsrc(d / 'c.mp4', 1.0, '180x320'))['w'], 180)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TestFilm(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.env = {k: os.environ.get(k) for k in ('VD_DRAFT_VOICE', 'VD_MUSIC_CACHE')}
        os.environ.update(VD_DRAFT_VOICE='offline-mock', VD_MUSIC_CACHE=str(self.d / 'music'))

    def tearDown(self):
        for k, v in self.env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        shutil.rmtree(self.d, ignore_errors=True)

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_a_clip_line_is_copied_drawn_labelled_and_credited(self):
        _testsrc(self.d / 'l1.mp4', 2.0)
        film = {'title': 't', 'brand': 'timekeeper', 'seed': 't', 'sources': ['[1] a source'],
                'lines': [{'id': 'l1', 'text': 'وكان الأب يعمل على القطارات', 'template': 'kinetic_type', 'set': 'paris_rail',
                           'banner': 'القطارات', 'params': {'lines': [{'text': 'القطارات', 'size': 60}]},
                           'clip': {'file': 'l1.mp4', 'label': clips.LABEL}}]}
        f = self.d / 'film.yaml'; f.write_text(yaml.safe_dump(film, allow_unicode=True), encoding='utf-8')
        r = quickfilm.make(f, self.d / 'out', video=False)
        self.assertTrue((self.d / 'out/assets/l1_clip.mp4').is_file())                              # copied into the film folder
        sc = json.loads((self.d / 'out/film.json').read_text())['scenes'][0]
        self.assertEqual(sc['elements'][0]['src'], 'assets/l1_clip.mp4')
        self.assertEqual(r['clips'][0]['mode'], 'replace')
        self.assertIn('l1: ' + clips.CREDIT, (self.d / 'out/credits.txt').read_text(encoding='utf-8'))
        self.assertEqual(r['layout'], []); self.assertEqual(r['stage'], [])
        self.assertFalse([q for q in r['quality'] if 'camera' in q])


@unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
class TestRender(unittest.TestCase):
    def test_a_two_second_clip_scene_renders_frame_by_frame(self):
        """A one-second clip whose every frame is a grey one step lighter than the last (frame n at 16 + 8n): the film's
        brightness reads back which clip frame was shown at each film frame, so the test sees the rate, the frame
        blending and the ping-pong, on two workers, and a still at the same time shows the same frame."""
        import numpy as np
        from PIL import Image
        d = Path(tempfile.mkdtemp())
        try:
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', "color=c=black:size=360x640:rate=24:duration=1,format=yuv420p,"
                            "geq=lum='16+N*8':cb=128:cr=128", '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(d / 'clip.mp4')], check=True)
            info = clips.probe(d / 'clip.mp4')
            tm = clips.timing(info['seconds'], 2.0)
            self.assertEqual(tm['rate'], .7); self.assertEqual(tm['after'], 'pingpong')
            sb = {'width': 720, 'height': 1280, 'fps': 10, 'scenes': [{'dur': 2.0, 'theme': 'teal', 'banner': 'clip', 'captions': 'one two',
                  'elements': [{'type': 'video', 'src': 'clip.mp4', 'w': 720, 'h': 1280, 'x': 360, 'y': 640, 'fit': 'cover',
                                'rate': tm['rate'], 'end': 'pingpong'}]}]}
            p = d / 'sb.json'; p.write_text(json.dumps(sb), encoding='utf-8')
            engine.video(p, d / 'out.mp4', scale=.25, workers=2)
            (d / 'f').mkdir()
            subprocess.run(['ffmpeg', '-v', 'error', '-i', str(d / 'out.mp4'), str(d / 'f/%03d.png')], check=True)
            grey = lambda f: float(np.asarray(Image.open(f).convert('L'))[110:190, 40:140].mean())   # clear of the banner and captions
            g = [grey(f) for f in sorted((d / 'f').glob('*.png'))]
            self.assertEqual(len(g), 20)
            shown = [24 * clips.clip_time(i / 10, tm['rate'], 23 / 24) for i in range(20)]           # the clip frame meant for each film frame
            a, b = np.polyfit(shown, g, 1)
            self.assertGreater(a, 5)
            self.assertLess(max(abs(y - (a * x + b)) for x, y in zip(shown, g)), 3.0)                # every frame the one meant, blended
            self.assertGreater(g[13], g[16])                                                         # past its end it runs backwards
            self.assertEqual(quality.frozen(d / 'out.mp4'), [])
            still = engine.stills(sb, d, [1.6], scale=.25)[0]                                        # the stills path shows the same frame
            self.assertAlmostEqual(grey(still), g[16], delta=3.0)
            self.assertTrue((d / '.clip-frames').is_dir())                                           # extracted once, shared by the workers
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
