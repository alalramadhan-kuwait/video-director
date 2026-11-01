"""`look: data` (the owner: the Altivère video's style): one dark stage, flat banners, clean prints, one ruby accent."""
from tests import _guard  # noqa: F401
import unittest

from director.studio import art, looks


class DataLook(unittest.TestCase):
    def test_paper_stays_the_default(self):
        self.assertEqual(looks.of({}), 'paper')
        with self.assertRaises(ValueError): looks.of({'look': 'neon'})
        base = art.style('timekeeper')
        self.assertIs(looks.style('paper', base), base)

    def test_the_banner_is_flat_and_the_grain_goes(self):
        st = looks.style('data', art.style('timekeeper'))['style']
        self.assertEqual(st['banner']['tape'], 'none'); self.assertEqual(st['banner']['torn'], 0)
        self.assertEqual(st['grain'], 0)
        self.assertEqual(st['caption']['bg'], '#141414')
        self.assertTrue(st['caption']['flat'])                                   # plain dark chips, no torn paper
        self.assertNotIn('Mono', st['banner']['font'])                           # a dotted 0 reads 1902 as 1982

    def test_prints_lie_flat_and_cards_are_dark(self):
        sc = art.scene_visual('archive_photo', {'asset': 'a', 'desc': 'd', 'aspect': 1.4, 'card': 'بطاقة'}, 'tk-bone', 4)
        looks.scene('data', sc)
        self.assertEqual(sc['theme'], 'tk-black')
        ph = [e for e in sc['elements'] if e['type'] == 'photo'][0]
        self.assertFalse(ph['polaroid']); self.assertEqual(ph['rot'], 0)
        card = [e for e in sc['elements'] if e['type'] == 'card'][0]
        self.assertEqual(card['style'], 'dark'); self.assertEqual(card['ink'], looks.SAND)

    def test_a_credit_sits_on_its_own_dark_band(self):
        sc = art.scene_visual('archive_photo', {'asset': 'a', 'desc': 'd', 'aspect': .7, 'credit': 'Joe Haupt · CC BY-SA 2.0'}, 'tk-bone', 4)
        looks.scene('data', sc)
        cr = [e for e in sc['elements'] if e.get('type') == 'text' and e.get('font') == 'cap'][0]
        self.assertEqual(cr['paper'], '#0B0B0B'); self.assertEqual(cr['color'], looks.SAND)

    def test_two_movements_light_17_and_21_jewels_the_four_extra_in_gold(self):
        els = art.scene_visual('technical_illustration', {'kind': 'jewels', 'counts': [17, 21], 'instant': True}, 'tk-black', 5)['elements']
        dots = [e for e in els if e.get('type') == 'shape']
        self.assertEqual(len(dots), 38)
        self.assertEqual(sum(1 for e in dots if e['color'] == art.GOLD), 4)
        self.assertEqual(sorted(e['text'] for e in els if e.get('type') == 'text' and e['text'].isdigit()), ['17', '21'])

    def test_a_hook_s_movements_show_their_numbers_on_frame_0(self):
        els = art.scene_visual('technical_illustration', {'kind': 'jewels', 'counts': [17, 21], 'instant': True}, 'tk-black', 5)['elements']
        nums = [e for e in els if e.get('type') == 'text' and e['text'].isdigit()]
        self.assertTrue(nums and all('in' not in e for e in nums))

    def test_the_end_card_logo_is_light_and_transparent_on_the_dark_stage(self):
        import shutil, tempfile
        from pathlib import Path
        from PIL import Image
        from director.studio import engine
        d = Path(tempfile.mkdtemp()); shutil.copyfile(engine.ENGINE / 'tk-logo-512.png', d / 'tk-logo-512.png')
        looks.endcard_logo('data', d); looks.endcard_logo('data', d)          # twice: the second run leaves it alone
        im = Image.open(d / 'tk-logo-512.png')
        self.assertEqual(im.mode, 'RGBA')
        lo, hi = im.getextrema()[3]
        self.assertEqual((lo, hi), (0, 255))
        looks.endcard_logo('paper', d)                                          # the paper look keeps its own logo

    def test_a_collage_print_can_be_there_from_frame_0(self):
        sc = art.scene_visual('archival_collage', {'photos': [{'asset': 'a', 'desc': 'd', 'at': 'none'}], 'tags': [{'text': 'x', 'at': 'none'}]}, 'tk-bone', 4)
        self.assertFalse(any('in' in e for e in sc['elements']))


if __name__ == '__main__':
    unittest.main()
