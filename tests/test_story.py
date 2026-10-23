"""The storytelling rules: historical events shown with historical photos, changes explained, feelings carried."""
from tests import _guard  # noqa: F401
import unittest

from director import quickfilm
from director.studio import art, engine, moods, sets


def film(*lines):
    return {'lines': [{'id': f'l{i}', 'text': 'x', 'template': 'kinetic_type', 'params': {}, 'no_photo': 'test', **ln}
                      for i, ln in enumerate(lines, 1)]}


class TestStory(unittest.TestCase):
    def test_an_event_needs_a_historical_photo_or_a_reason(self):
        self.assertIn('no historical photo', quickfilm.story_check(film({'event': True, 'mood': 'fear', 'no_photo': None}))[0])
        self.assertEqual(quickfilm.story_check(film({'event': True, 'mood': 'fear', 'template': 'archive_photo', 'params': {'asset': 'p'}}))[:0], [])
        self.assertEqual(quickfilm.story_check(film({'event': True, 'mood': 'fear', 'no_photo': 'no photo was ever taken'})), [])

    def test_a_change_needs_its_reason_and_a_story_needs_its_feeling(self):
        out = quickfilm.story_check(film({'change': True}, {'event': True, 'template': 'archive_photo'}))
        self.assertTrue(any('without its reason' in o for o in out))
        self.assertTrue(any('feeling' in o for o in out))
        self.assertTrue(any('unknown mood' in o for o in quickfilm.story_check(film({'mood': 'happyish'}))))

    def test_the_story_is_told_in_order(self):
        out = quickfilm.story_check(film({'text': 'في 1936'}, {'text': 'في 1915'}))
        self.assertTrue(any('out of order' in o for o in out))
        self.assertEqual(quickfilm.story_check(film({'text': 'في 1936'}, {'text': 'في 1915', 'flashback': True})), [])
        self.assertEqual(quickfilm.story_check(film({'text': 'من 1860 إلى 1915'}, {'text': 'في 1936'})), [])

    def test_each_scene_shows_only_what_is_said_in_it(self):
        ok = film({'text': 'طلبت البحرية ساعة في 1936', 'banner': 'طلب البحرية', 'params': {'lines': [{'text': '1936'}]}})
        self.assertEqual(quickfilm.story_check(ok), [])
        bad = film({'text': 'طلبت البحرية ساعة', 'banner': 'لومينور مارينا', 'params': {'lines': [{'text': '1860'}]}})
        out = quickfilm.story_check(bad)
        self.assertTrue(any('«لومينور مارينا»' in o for o in out) and any('«1860»' in o for o in out))
        self.assertEqual(quickfilm.story_check(film({'text': 'x', 'banner': 'غير مقال', 'screen_ok': True})), [])
        sc = quickfilm.on_screen({'banner': 'ب', 'params': {'rows': [{'label': 'ل', 'value': 'ق'}], 'credit': 'c', 'source': 's', 'asset': 'a'}})
        self.assertEqual(sorted(sc), ['ب', 'ق', 'ل'])                              # credits, sources and slots are not "what is shown"

    def test_every_change_of_scene_is_led_into(self):
        out = quickfilm.story_check(film({'text': 'البداية'}, {'text': 'عاملات في أمريكا'}))
        self.assertTrue(any('without leading in' in o for o in out))
        for first in ('وفي أمريكا', 'غير أن الضوء', 'لكن البحرية', 'ثم انتهت', 'وبينما كان'):
            self.assertEqual(quickfilm.story_check(film({'text': 'البداية'}, {'text': first})), [], first)
        self.assertEqual(quickfilm.story_check(film({'text': 'البداية'}, {'text': 'ساعة وُلدت', 'closing': True})), [])

    def test_every_scene_has_a_picture_of_its_own_time(self):
        f = film({'text': 'البداية', 'template': 'drawing'}, {'text': 'وفي 1949', 'no_photo': None})          # the opening is drawn; the rest need a picture
        self.assertTrue(any('l2: no picture' in o for o in quickfilm.story_check(f)))
        f = {**film({'text': 'البداية', 'template': 'drawing'}, {'text': 'وفي 1949', 'photo': 'w'}), 'photos': {'w': {'query': 'q', 'year': 2016}}}
        self.assertTrue(any('photo is from about 2016' in o for o in quickfilm.story_check(f)))
        f = {**film({'text': 'البداية', 'template': 'drawing'}, {'text': 'وفي 1949', 'photo': 'w'}), 'photos': {'w': {'query': 'q', 'year': 1956}}}
        self.assertEqual(quickfilm.story_check(f), [])
        self.assertEqual(quickfilm.story_check(film({'text': 'x', 'template': 'city_zoom', 'no_photo': None, 'params': {'city': 'kuwait'}})), [])

    def test_words_over_a_photo_stay_readable(self):
        sc = art.backdrop(art.scene_visual('kinetic_type', {'lines': [{'text': 'x'}]}, 'tk-ink', 5.0), 'w', 5.0, credit='A · PD')
        self.assertEqual(sc['elements'][0]['asset'], 'w'); self.assertTrue(sc['elements'][0]['behind'])
        self.assertIn('fill-opacity=".62"', sc['elements'][1]['svg'])
        self.assertTrue(sc['full_frame']); self.assertTrue(any(e.get('text') == 'A · PD' for e in sc['elements']))

    def test_the_opening_is_drawn_not_a_photo(self):
        out = quickfilm.story_check(film({'text': 'x', 'template': 'archive_photo', 'params': {'asset': 'p'}}))
        self.assertTrue(any('opening should hook with a drawing' in o for o in out))
        self.assertFalse(any('opening' in o for o in quickfilm.story_check(film({'text': 'x', 'template': 'drawing'}))))
        sc = art.scene_visual('drawing', {'subject': 'watch', 'lines': [{'text': 'x'}], 'torpedo': {'at': 2}, 'stamp': {'text': 's'}}, 'tk-ink', 6.0)
        kinds = [e['type'] for e in sc['elements']]
        self.assertIn('sketch', kinds); self.assertIn('stamp', kinds)
        self.assertEqual({c['name'] for c in sc['sfx']} >= {'chime', 'bubbles', 'stamp'}, True)
        self.assertTrue(art.production_ready('drawing'))

    def test_the_panerai_film_keeps_every_rule(self):
        self.assertEqual(quickfilm.story_check(quickfilm.load(engine.ROOT / 'films/panerai.yaml')), [])

    def test_every_mood_grades_the_scene_under_the_words_and_has_a_sound(self):
        kit = (engine.ENGINE / 'scripts/make-sfx.py').read_text()
        for m in moods.MOODS:
            sc = moods.dress(art.scene_visual('kinetic_type', {'lines': [{'text': 'x'}]}, 'tk-bone', 5.0), m, 5.0)
            added = [e for e in sc['elements'] if e.get('z') == moods.Z]
            self.assertTrue(added, m)                                                   # under the banner (900) and captions (950)
            sounds = sc.get('beds', []) + [c for c in sc.get('sfx', []) if c['name'] in ('chime',)]
            self.assertTrue(sounds, m)
            for c in sounds: self.assertIn(f"save('{c['name']}'", kit, m)
            self.assertEqual(sc['mood'], m)

    def test_a_tall_photo_fills_the_frame_a_wide_one_is_a_print(self):
        tall = art.scene_visual('archive_photo', {'asset': 'a', 'desc': 'd', 'aspect': .7, 'card': 'x', 'credit': 'A · PD'}, 'tk-bone', 6.0)
        wide = art.scene_visual('archive_photo', {'asset': 'a', 'desc': 'd', 'aspect': 1.5}, 'tk-bone', 6.0)
        self.assertTrue(tall['full_frame']); self.assertEqual(tall['elements'][0]['fit'], 'cover')
        self.assertFalse(wide['full_frame']); self.assertEqual(wide['elements'][0]['type'], 'photo')
        self.assertTrue(any(e.get('text') == 'A · PD' for e in tall['elements']))             # the credit on screen
        n = len(tall['elements'])
        sets.dress(tall, 'underwater', 6.0, template='archive_photo')
        self.assertEqual(len(tall['elements']), n)                                          # a full photo is the world itself


class TestRulesLiveInThePlugin(unittest.TestCase):
    def test_the_owner_standards_ship_with_the_plugin_and_the_studio(self):
        from director.copilot import ai
        for root in ('skills', '.claude/skills'):
            rules = (engine.ROOT / root / 'video-director/references/storytelling.md').read_text()
            for must in ('In order', 'led into', 'Explain why', 'Sadness for human moments', 'historical photograph',
                         'Each scene shows only what is said', 'Never imply a link', 'city_zoom', 'merge your own pull requests'):
                self.assertIn(must, rules, (root, must))
            self.assertIn('references/storytelling.md', (engine.ROOT / root / 'video-director/SKILL.md').read_text())
        self.assertIn('chronological order', ai.SYSTEM['script'])
        self.assertIn('only what its own line says', ai.system_prompt('art_brief'))
