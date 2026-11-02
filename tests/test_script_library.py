"""The script library (the owner: «build a library to guide the video type from this script… light Arabic or Kuwaiti
or TK style, with examples»): types with acts and lengths, three languages with rules and examples."""
from tests import _guard  # noqa: F401
import unittest

from director import quickfilm, scripts


def film(lines, **kw):
    return {'brand': 'timekeeper', 'lines': [{'id': f'l{i}', 'text': t, 'template': 'kinetic_type', 'params': {}, 'no_photo': 't', **x}
                                             for i, (t, x) in enumerate(lines, 1)], **kw}


class Library(unittest.TestCase):
    def test_every_type_is_whole(self):
        for k, T in scripts.types().items():
            self.assertAlmostEqual(sum(a['share'] for a in T['acts']), 1.0, places=6, msg=k)
            self.assertTrue(set(T['languages']) <= set(scripts.languages()), k)
            lo, hi = T['seconds']; self.assertLess(lo, hi, k)
            self.assertTrue(all(a['example'] for a in T['acts']), k)

    def test_three_languages_each_with_rules_and_the_same_three_example_lines(self):
        self.assertEqual(set(scripts.languages()), {'tk', 'light', 'kuwaiti'})
        for k, L in scripts.languages().items():
            self.assertTrue(L['rules'], k)
            self.assertEqual(set(L['example']), {'hook', 'line', 'close'}, k)
        self.assertEqual(scripts.default_language(), 'tk')
        self.assertIn('caution', scripts.languages()['kuwaiti'])          # Halter: full Kuwaiti voiced badly; test first

    def test_a_card_shows_the_acts_and_the_example(self):
        c = scripts.card('numbers_explainer', 'kuwaiti')
        self.assertIn('شرح بالأرقام', c); self.assertIn('كويتي', c)
        self.assertIn(scripts.languages()['kuwaiti']['example']['hook'], c)


class Checks(unittest.TestCase):
    def test_light_arabic_has_no_dialect(self):
        f = film([('ليش داخل ساعتك ياقوت؟', {'cold_open': True}), ('لأن المحاور كانت تتآكل', {})], language='light')
        self.assertTrue(any('«ليش»' in m for m in scripts.check(f)))
        f['lines'][0]['text'] = 'لماذا يوجد ياقوت داخل ساعتك؟'
        self.assertEqual([m for m in scripts.check(f) if 'belong' in m], [])

    def test_kuwaiti_in_tk_is_a_light_touch(self):
        mid = [('وايد ناس ما يعرفون', {}), ('شلون صار جذي', {}), ('ليش؟', {}), ('بس اللي يشتغل 17', {})]
        f = film([('شنو الفرق؟', {'cold_open': True})] + mid + [('وساعتك شكم حبة فيها؟', {'closing': True})])
        self.assertTrue(any('light touch' in m for m in scripts.check(f)))
        f['language'] = 'kuwaiti'
        self.assertEqual([m for m in scripts.check(f) if 'light touch' in m], [])

    def test_the_type_sets_the_length_before_any_voice(self):
        f = film([('كلمة ' * 200, {})], script_type='viewer_question')
        est = scripts.estimate(f)
        self.assertGreater(est['seconds'], 40)
        self.assertTrue(any('cut a fact' in m for m in scripts.check(f)))

    def test_unknown_type_or_language_is_named(self):
        self.assertTrue(scripts.check(film([('سطر', {})], language='fusha'))[0].startswith('language'))
        self.assertTrue(any(m.startswith('script_type') for m in scripts.check(film([('سطر', {})], script_type='vlog'))))

    def test_story_check_carries_it_and_the_news_words_stay_tk(self):
        f = film([('ساعة من الفولاذ', {})], language='light')
        msgs = quickfilm.story_check(f)
        self.assertFalse(any('فولاذ' in m for m in msgs))                # fine fusha outside Time Keeper style
        f['language'] = 'tk'
        self.assertTrue(any('فولاذ' in m for m in quickfilm.story_check(f)))
        f = film([('ليش؟', {})], language='light')
        self.assertTrue(any('«ليش»' in m for m in quickfilm.story_check(f)))


if __name__ == '__main__':
    unittest.main()
