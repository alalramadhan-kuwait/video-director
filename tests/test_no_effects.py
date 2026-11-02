"""The owner on Halter 2 v4: «شيل كل المؤثرات الصوتية». `effects: none` in a film file leaves the voice and the
music: no one-shot and no bed in any scene, the end card included."""
from tests import _guard  # noqa: F401
import unittest

from director.studio import mix


class NoEffects(unittest.TestCase):
    def test_the_switch(self):
        for v in ('none', 'off', 'None', False, 'false'):
            self.assertTrue(mix.silent({'effects': v}), v)
        for f in ({}, {'effects': True}, {'effects': 'some'}):
            self.assertFalse(mix.silent(f), f)

    def test_every_cue_and_bed_goes(self):
        scenes = [{'id': 'a', 'dur': 3, 'sfx': [{'name': 'gavel', 'at': 1}], 'beds': [{'name': 'tick', 'gain': -30}]},
                  {'id': 'end', 'dur': 2, 'endcard': True, 'sfx': [{'name': 'tick', 'at': 0.5}]}]
        self.assertEqual(mix.silence(scenes), 3)
        self.assertTrue(all(not s['sfx'] and not s['beds'] for s in scenes))

    def test_the_film_builder_uses_it(self):
        from pathlib import Path
        src = (Path(mix.__file__).resolve().parents[1] / 'quickfilm.py').read_text(encoding='utf-8')
        self.assertIn('mix.silent(film)', src)
        self.assertIn('mix.silence(scenes + ending)', src)


if __name__ == '__main__':
    unittest.main()
