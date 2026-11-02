"""The owner on Halter 2 v5: «شيل الموسيقى وعدل الصوت في تضخم». A boomy narration take is evened out before the mix
(voice.tone), and a film can leave its music out (`music: none`)."""
from tests import _guard  # noqa: F401
import unittest
from pathlib import Path

import numpy as np

from director.studio import voice


def tones(*hz_amp, secs=2.0):
    t = np.arange(int(voice.SR * secs)) / voice.SR
    return sum(a * np.sin(2 * np.pi * h * t) for h, a in hz_amp)


class Tone(unittest.TestCase):
    def test_a_boomy_take_is_evened_out(self):
        a = tones((110, .4), (1000, .1))
        self.assertGreater(voice.low_share(a), voice.BOOM_DB)
        def lows_over_highs(x):                       # dB of 60–150 Hz against 150 Hz up
            s = np.abs(np.fft.rfft(x)) ** 2; hz = np.fft.rfftfreq(len(x), 1 / voice.SR)
            return 10 * np.log10(s[(hz >= 60) & (hz < 150)].sum() / s[hz >= 150].sum())
        self.assertLess(lows_over_highs(voice.tone(a)), lows_over_highs(a) - 6)

    def test_a_clear_take_stays_as_it_is(self):
        a = tones((110, .05), (1000, .4))
        self.assertLess(voice.low_share(a), voice.BOOM_DB)
        self.assertIs(voice.tone(a), a)

    def test_the_film_builder_uses_both(self):
        src = (Path(voice.__file__).resolve().parents[1] / 'quickfilm.py').read_text(encoding='utf-8')
        self.assertIn('a = voice.tone(a if cont else voice.trim(a), boom)', src)
        self.assertIn('mus = None if no_music else', src)


if __name__ == '__main__':
    unittest.main()
