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
        self.assertGreater(short['gain'], long_['gain'] + 8)


if __name__ == '__main__':
    unittest.main()
