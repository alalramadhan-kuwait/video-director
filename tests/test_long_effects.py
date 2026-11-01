from tests import _guard  # noqa: F401
import tempfile, unittest, wave
from pathlib import Path

import numpy as np

from director.studio import mix


def tone(path, secs, amp=.5):
    x = (amp * np.sin(np.arange(int(44100 * secs)) * 2 * np.pi * 220 / 44100) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100); w.writeframes(x.tobytes())


class TestLongEffects(unittest.TestCase):
    def test_a_long_effect_sits_like_a_bed_and_a_short_one_hits(self):
        d = Path(tempfile.mkdtemp())
        tone(d / 'longone.wav', 6); tone(d / 'shortone.wav', .8)
        sc = [{'sfx': [{'at': 0, 'name': 'longone', 'gain': -10}, {'at': 1, 'name': 'shortone', 'gain': -10}]}]
        mix.levels(sc, {0: -20.0}, sfx_dir=d)
        lv = mix.level(str(d / 'longone.wav'), 'active')
        long_, short = sc[0]['sfx']
        self.assertAlmostEqual(-20 - (lv + long_['gain']), mix.LONG_UNDER, delta=.2)
        peak = mix.level(str(d / 'shortone.wav'), 'peak')
        self.assertGreaterEqual(-20 + 3 - (peak + short['gain']), mix.SHOT_UNDER[0] - .2)   # a hit is felt, not heard


    def test_a_strike_with_a_long_tail_is_still_a_hit(self):
        d = Path(tempfile.mkdtemp())
        tone(d / 'tower_strike.wav', 4)
        sc = [{'sfx': [{'at': 0, 'name': 'tower_strike', 'gain': -10}]}]
        mix.levels(sc, {0: -20.0}, sfx_dir=d)
        peak = mix.level(str(d / 'tower_strike.wav'), 'peak')
        self.assertLessEqual(-20 + 3 - (peak + sc[0]['sfx'][0]['gain']), mix.SHOT_UNDER[1] + .2)   # a hit, 16-20 dB under the voice's peaks


if __name__ == '__main__':
    unittest.main()
