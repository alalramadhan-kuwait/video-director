"""One narrator telling one story (the owner, 2 Nov 2026, on Halter 2: «Each scene sounds like a separate recording…
The narrator is telling one continuous story, not performing each scene independently»)."""
from tests import _guard  # noqa: F401
import json, tempfile, unittest
from pathlib import Path

import numpy as np

from director import narration, quickfilm


def L(i, tone=None, act=False):
    return {'id': i, **({'tone': tone} if tone else {}), **({'act': True} if act else {})}


def voice(f0=120.0, amp=.2, secs=2.0, sr=24000):
    t = np.arange(int(sr * secs)) / sr
    return amp * (np.sin(2 * np.pi * f0 * t) + .5 * np.sin(4 * np.pi * f0 * t))


class Plan(unittest.TestCase):
    def test_a_line_without_a_tone_carries_the_one_before(self):
        self.assertEqual([p['tone'] for p in narration.plan([L('a', 'warm'), L('b'), L('c', 'curious')])], ['warm', 'warm', 'curious'])

    def test_an_arc_that_builds_passes(self):
        lines = [L('a', 'curious'), L('b', 'warm'), L('c', 'curious'), L('d', 'surprised'), L('e', 'curious'), L('f', 'warm')]
        self.assertEqual(narration.check(lines), [])

    def test_no_reset_at_a_new_act(self):
        m = narration.check([L('a', 'curious'), L('b', 'surprised'), L('c', 'calm', act=True)])
        self.assertTrue(any('start of an act' in x for x in m))

    def test_surprise_is_rare_and_the_opening_is_not_a_shout(self):
        m = narration.check([L('a', 'excited'), L('b', 'surprised'), L('c', 'excited')])
        self.assertTrue(any('opening' in x for x in m))
        self.assertTrue(any('keep it for' in x for x in m))


class Review(unittest.TestCase):
    def test_one_voice_passes(self):
        self.assertEqual(narration.review([('a', voice(), 24000, 30), ('b', voice(), 24000, 30)]), [])

    def test_a_new_recording_is_heard(self):
        m = narration.review([('a', voice(), 24000, 30), ('b', voice(150, .6), 24000, 30)])
        self.assertTrue(any('loudness' in x for x in m) and any('pitch' in x for x in m))


class Continuous(unittest.TestCase):
    def test_a_piece_of_one_narration_is_known_by_its_record(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'l1.json').write_text(json.dumps({'continuous': True}), encoding='utf-8')
            (Path(d) / 'l2.json').write_text(json.dumps({'act': 1}), encoding='utf-8')
            self.assertTrue(quickfilm.continuous(Path(d) / 'l1.wav'))
            self.assertFalse(quickfilm.continuous(Path(d) / 'l2.wav'))
            self.assertFalse(quickfilm.continuous(Path(d) / 'l3.wav'))

    def test_the_scenes_follow_the_audio(self):
        src = Path(quickfilm.__file__).read_text(encoding='utf-8')
        self.assertIn("v_at = (VOICE_AT if k == 0 else 0.0) if flow else VOICE_AT", src)
        self.assertIn("dur = round(v_at + t['seconds'], 2) if flow", src)
        self.assertIn("a = voice.tone(a if cont else voice.trim(a), boom)", src)

    def test_the_recorder_reads_the_whole_script(self):
        src = (Path(quickfilm.__file__).resolve().parents[1] / 'tools/record_flow.py').read_text(encoding='utf-8')
        self.assertIn("groups = [film['lines']] if whole else acts(film['lines'])", src)
        self.assertIn("narration.check(film['lines'])", src)


if __name__ == '__main__':
    unittest.main()
