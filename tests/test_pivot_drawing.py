"""The pivot in its bearing, in section (the rubies film): brass, worn, jewel. A principle, never a calibre."""
from tests import _guard  # noqa: F401
import json, unittest

from director.studio import art


def scene(stage, **kw):
    return art.scene_visual('technical_illustration', {'kind': 'pivot', 'stage': stage, **kw}, 'tk-bone', 5)


class Pivot(unittest.TestCase):
    def test_each_stage_draws_and_says_it_is_a_principle(self):
        for st in ('brass', 'worn', 'jewel'):
            sc = scene(st)
            self.assertIn(art.DRAWING_NOTE, json.dumps(sc, ensure_ascii=False))

    def test_the_worn_hole_takes_the_brass_hole_s_place_and_the_axle_wobbles(self):
        els = scene('worn', wear_at=1.0)['elements']
        self.assertTrue(any(e.get('opacity') == [[0, 1], [1.0, 1], [1.5, 0]] for e in els))     # the narrow hole fades out
        self.assertTrue(any(e.get('in', {}).get('at') == 1.0 for e in els))                    # the wide one fades in
        self.assertTrue(any(e.get('rot') for e in els))                                         # the axle wobbles

    def test_the_jewel_is_ruby_red_and_labelled(self):
        s = json.dumps(scene('jewel'), ensure_ascii=False)
        self.assertIn(art.RUBY, s)
        self.assertIn('ياقوتة مثقوبة', s)


if __name__ == '__main__':
    unittest.main()
