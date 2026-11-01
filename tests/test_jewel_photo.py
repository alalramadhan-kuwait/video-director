"""Real movement photos with their visible jewels ringed (the owner: «ليش ماتستخدم تصميم لمحرك حقيقي»)."""
from tests import _guard  # noqa: F401
import unittest

from director import quickfilm
from director.studio import art

OMEGA = {'asset': 'm17', 'desc': 'Omega 321', 'aspect': .9, 'count': 17, 'label': 'أوميغا 321', 'credit': 'Shane Lin · CC BY-SA 2.0',
         'marks': [[.5, .25], [.48, .49], [.77, .56]]}
MIYOTA = {'asset': 'm21', 'desc': 'Miyota 8215', 'aspect': 1.0, 'count': 21, 'label': 'ميوتا 8215', 'marks': [[.26, .33]]}


class JewelPhoto(unittest.TestCase):
    def els(self, prints, **kw):
        return art.scene_visual('jewel_photo', {'prints': prints, **kw}, 'tk-black', 4)['elements']

    def test_it_is_ready_and_needs_its_photos(self):
        self.assertTrue(art.production_ready('jewel_photo'))
        self.assertEqual(art.NEEDS_ASSETS['jewel_photo']({'prints': [OMEGA, MIYOTA]}), ['m17', 'm21'])
        self.assertIn('jewel_photo', quickfilm.PHOTO_TEMPLATES)

    def test_each_visible_jewel_is_ringed_on_the_photo_in_turn(self):
        els = self.els([OMEGA])
        ph = next(e for e in els if e['type'] == 'photo')
        rings = [e for e in els if e['type'] == 'svg']
        self.assertEqual(len(rings), len(OMEGA['marks']))
        h = ph['w'] / ph['aspect']
        for r, (fx, fy) in zip(rings, OMEGA['marks']):                     # on the jewel the photo shows, inside the print
            self.assertAlmostEqual(r['x'], ph['x'] - ph['w'] / 2 + fx * ph['w'], places=0)
            self.assertAlmostEqual(r['y'], ph['y'] - h / 2 + fy * h, places=0)
        ats = [r['in']['at'] for r in rings]
        self.assertEqual(ats, sorted(ats)); self.assertEqual(len(set(ats)), len(ats))

    def test_the_count_lands_after_the_rings_below_the_print(self):
        els = self.els([OMEGA])
        ph = next(e for e in els if e['type'] == 'photo')
        num = next(e for e in els if e['type'] == 'text' and e['text'] == '17')
        last = max(e['in']['at'] for e in els if e['type'] == 'svg')
        self.assertGreater(num['in']['at'], last)
        self.assertGreater(num['y'] - num['size'] / 2, ph['y'] + ph['w'] / ph['aspect'] / 2)   # never over the photo
        label = next(e for e in els if e.get('text') == 'أوميغا 321')
        self.assertGreater(label['y'], num['y'] + num['size'] / 2)                              # the calibre's name under its number

    def test_two_prints_sit_side_by_side_inside_the_frame_from_frame_0(self):
        els = self.els([OMEGA, MIYOTA], instant=True)
        phs = [e for e in els if e['type'] == 'photo']
        self.assertGreater(phs[0]['x'], phs[1]['x'])                       # the first on the right (RTL)
        for ph in phs:
            self.assertGreaterEqual(ph['x'] - ph['w'] / 2, 40); self.assertLessEqual(ph['x'] + ph['w'] / 2, 680)
            self.assertNotIn('in', ph)
        self.assertFalse(any('in' in e for e in els if e['type'] == 'text'))
        self.assertEqual({e['text'] for e in els if e['type'] == 'text' and e['text'].isdigit()}, {'17', '21'})


if __name__ == '__main__':
    unittest.main()
