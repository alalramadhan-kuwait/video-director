"""The house rules gate (the owner, 8 Nov 2026: «after writing a text, is there a gateway that will check all those
rules… so all those edits will not go to waste»)."""
from tests import _guard  # noqa: F401
import unittest

from director import house


class Gate(unittest.TestCase):
    def test_every_owner_correction_is_caught(self):
        for bad in ('بحركة من 320 قطعة', 'العلبة من الذهب', 'ميزان قطره 20 ملم', 'شعرة زنبرك رفيعة',
                    'بلا جسر علوي', 'تعمل 406 أيام', 'أول كرونوغراف لركسهيبي', '1,240 قطع'):
            self.assertTrue(house.check(bad, 'x'), bad)

    def test_clean_text_passes(self):
        for good in ('بمحرك من 320 قطعة', 'المحرك والقالب من الذهب', 'بالانس ويل بحجم 20 ملم', 'تعمل 406 يوم',
                     'أول كرونوغراف لرجب رجبي', 'سماكتها 6.9 ملم', 'خلال 11,000 ساعة عمل', 'ساعتين', '10 أيام'):
            self.assertEqual(house.check(good, 'x'), [], good)

    def test_safe_fixes_are_rewritten(self):
        self.assertEqual(house.fix('شعرة زنبرك ورجل اسمه ركسهيب ركسهيبي'), 'هير سبرينغ ورجل اسمه رجب رجبي')
        self.assertEqual(house.fix('بلا جسر علوي'), 'بلا بريدج علوي')

    def test_a_flagged_word_can_be_confirmed_for_one_film(self):
        lines = [{'text': 'تبدأ من حركة صغيرة من إيدك'}]
        self.assertTrue(house.check_lines(lines))
        self.assertEqual(house.check_lines(lines, ok=['حركة']), [])

    def test_diacritics_do_not_hide_a_word(self):
        self.assertTrue(house.check('ينلف زنْبرك صْغير', 'x'))

    def test_a_caption_has_no_hashtags_or_sources(self):
        self.assertTrue(house.check('خبر\n#ساعات', 'c', caption=True))
        self.assertTrue(house.check('خبر\nالمصادر: موقع', 'c', caption=True))
        self.assertEqual(house.check('خبر قصير.\nوأنت؟', 'c', caption=True), [])

    def test_a_carousel_is_checked_whole(self):
        spec = {'cover': {'top': 'عنوان', 'bottom': ''}, 'slides': [{'title': 'جائزة', 'body': 'بحركة جديدة'}]}
        self.assertTrue(any(m.startswith('slide 1') for m in house.check_carousel(spec, 'كابشن #هاشتاق')))
        self.assertTrue(any(m.startswith('caption') for m in house.check_carousel(spec, 'كابشن #هاشتاق')))


if __name__ == '__main__':
    unittest.main()
