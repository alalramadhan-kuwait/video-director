"""The owner's Kuwaiti word book is applied before any take, and new risky words stop the take before it is paid for
(the owner, 7 Nov 2026: «هل يتعلم من تصليح الاغلاط… متعب كل مره يرد يسجل»)."""
import unittest

from director import kw

W = [{'word': 'ليش', 'say': 'ليْش', 'kind': 'auto'}, {'word': 'الساعة', 'say': 'السّاعه', 'kind': 'auto'},
     {'word': 'عقب', 'say': 'بعد', 'kind': 'ask', 'note': 'بعد over عقب'}]


class WordBook(unittest.TestCase):
    def test_auto_words_with_joined_letters(self):
        self.assertEqual(kw.apply('ليش إذا فتحت', W), 'ليْش إذا فتحت')
        self.assertEqual(kw.apply('وبالساعة، قطع الساعة.', W), 'وبالسّاعه، قطع السّاعه.')
        self.assertEqual(kw.apply('الساعات كثيرة', W), 'الساعات كثيرة')        # a longer word is not touched

    def test_feminine_ha_gets_its_sukun(self):
        self.assertEqual(kw.apply('داخلها بتصاميمها', []), 'داخلْها بتصاميمْها')
        self.assertEqual(kw.apply('داخلْها لها', []), 'داخلْها لها')           # already marked, or too short
        self.assertEqual(kw.apply('معاها فيها عليها', []), 'معاها فيها عليها')   # never on a long vowel

    def test_idempotent(self):
        once = kw.apply('ليش الساعة', W)
        self.assertEqual(kw.apply(once, W), once)

    def test_ask_and_new_words_are_flagged(self):
        got = kw.check([{'say': 'عقب الحرب صار قانون جديد'}], words=W, known={'صار', 'الحرب'})
        kinds = {(g['kind'], g['word']) for g in got}
        self.assertIn(('ask', 'عقب'), kinds)
        self.assertIn(('new', 'قانون'), kinds)
        self.assertIn(('new', 'جديد'), kinds)

    def test_known_marked_and_cleared_words_pass(self):
        lines = [{'say': 'قانون جديد قَديمة'}]
        self.assertEqual(kw.check(lines, ok=['قانون', 'جديد'], words=W, known=set()), [])

    def test_real_book_loads_and_covers_the_picks(self):
        b = {e['word']: e for e in kw.book()}
        for w, s in [('ليش', 'ليْش'), ('الساعة', 'السّاعه'), ('قديمة', 'قَديمة'), ('بعثة', 'بِعْثة'), ('قبلها', 'قبلْها'), ('ماي', 'مايْ')]:
            self.assertEqual(b[w]['say'], s)
            self.assertEqual(b[w]['kind'], 'auto')
        self.assertTrue(all('گ' not in e['say'] for e in b.values()))   # never write «گ»


if __name__ == '__main__':
    unittest.main()
