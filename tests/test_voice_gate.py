"""The voice gate (the owner, 10 Nov 2026: «there should be a gateway where if the rules are not applied it will not
record»): tools/record_flow.py stops before anything is paid for, with no override for the spoken text."""
from tests import _guard  # noqa: F401
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from director import voice_gate
from tools import record_flow


class Spoken(unittest.TestCase):
    def test_digits_never_reach_the_voice(self):
        p = voice_gate.spoken_problems(['تروح وترد 8 دقات… 28,800 دقة بالساعة'])
        self.assertTrue(any('digits' in x for x in p))
        self.assertEqual(voice_gate.spoken_problems(['ثمانية وعشرين ألف وثمانمية دقة بالساعة']), [])

    def test_watch_terms_are_spoken_in_english_other_english_is_not(self):
        # the owner, 10 Nov 2026: «مفروض نطق الكلامات الانجليزية بالانجليزي هذي قاعده» (voice.say_english)
        self.assertEqual(voice_gate.spoken_problems(['نلف Mainspring داخل Barrel']), [])
        self.assertEqual(voice_gate.spoken_problems(['نلف المين سبرينغ داخل الباريل']), [])
        self.assertTrue(voice_gate.spoken_problems(['هذا Superlative']))

    def test_spoken_english_terms_still_stay_off_the_screen(self):
        self.assertTrue(voice_gate.screen_problems([{'text': 'نلف Mainspring', 'screen': ''}]))
        self.assertTrue(voice_gate.screen_problems([{'text': 'نلف المين سبرينغ', 'screen': '1 · Mainspring'}]))

    def test_words_the_owner_cleared_by_ear_and_names_pass(self):
        self.assertEqual(voice_gate.spoken_problems(['ساعة Oyster']), [])
        self.assertEqual(voice_gate.spoken_problems(['بيعت في مزاد Phillips'], names=['Phillips']), [])
        self.assertTrue(voice_gate.spoken_problems(['بيعت في مزاد Phillips']))

    def test_article_before_english_and_gaf(self):
        self.assertTrue(any('«ال»' in x for x in voice_gate.spoken_problems(['نلف الـ Mainspring'])))
        self.assertTrue(any('گ' in x for x in voice_gate.spoken_problems(['تگطع'])))


class Screen(unittest.TestCase):
    def test_screen_words_are_arabic_digits_stay(self):
        self.assertTrue(voice_gate.screen_problems([{'text': 'نلف الزنبرك', 'screen': '1 · MAINSPRING'}]))
        self.assertTrue(voice_gate.screen_problems([{'text': 'نلف الـ Mainspring', 'screen': ''}]))
        self.assertEqual(voice_gate.screen_problems([{'text': 'نلف المين سبرينغ', 'screen': '1 · مين سبرينغ · 28,800'}]), [])


class Recording(unittest.TestCase):
    def run_flow(self, lines, *extra, **top):
        d = Path(tempfile.mkdtemp())
        (d / 's.json').write_text(json.dumps({'lines': lines, 'kw_ok': top.get('kw_ok', []), 'rules_ok': top.get('rules_ok', [])},
                                             ensure_ascii=False), encoding='utf-8')
        with mock.patch.object(record_flow, 'speak', side_effect=RuntimeError('PAID')) as sp:
            try:
                rc = record_flow.main([str(d / 's.json'), str(d / 'v'), '--voice', 'x', *extra])
            except RuntimeError as e:
                rc = str(e)
        gate = json.loads((d / 'v' / 'gate.json').read_text(encoding='utf-8')) if (d / 'v' / 'gate.json').exists() else None
        return rc, sp.called, gate

    def test_a_broken_script_is_never_recorded(self):
        rc, paid, gate = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية', 'say': 'ساعة فيها 8 دقات'}],
                                       kw_ok=['ساعة', 'بدون', 'بطارية', 'فيها', 'دقات'])
        self.assertEqual(rc, 5); self.assertFalse(paid); self.assertFalse(gate['passed'])

    def test_english_on_screen_stops_it_too(self):
        rc, paid, _ = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية', 'screen': 'NO BATTERY'}], kw_ok=['ساعة', 'بدون', 'بطارية'])
        self.assertEqual(rc, 5); self.assertFalse(paid)

    def test_overrides_need_the_owners_words(self):
        rc, paid, _ = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية'}], '--rules-ok')
        self.assertEqual(rc, 6); self.assertFalse(paid)

    def test_a_clean_script_reaches_the_voice(self):
        rc, paid, gate = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية'}], kw_ok=['ساعة', 'بدون', 'بطارية'])
        self.assertEqual(rc, 'PAID'); self.assertTrue(paid); self.assertTrue(gate['passed'])


if __name__ == '__main__':
    unittest.main()
