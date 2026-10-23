"""Story worlds dress any template without covering it; their sounds exist; templates carry their own sound effects."""
from tests import _guard  # noqa: F401
import unittest

from director.studio import art, engine, sets


class TestSets(unittest.TestCase):
    def test_every_world_dresses_a_scene_behind_and_at_the_edges(self):
        for k in sets.SETS:
            base = art.scene_visual('map', {'view': {'lon': 11, 'lat': 43, 'span': 6}}, sets.theme_for(k, 'tk-bone'), 6.0)
            own = list(base['elements'])
            sc = sets.dress(base, k, 6.0, seed='x', template='kinetic_type')
            i = sc['elements'].index(own[0])
            self.assertTrue(all(e.get('behind') for e in sc['elements'][:i]), k)            # back decor under the template
            self.assertTrue(all(not e.get('behind') for e in sc['elements'][i + len(own):]), k)   # front decor over it (a full map too)
            self.assertTrue(sc['beds'], k)
            for e in sc['elements'][:i]:
                self.assertNotEqual(e.get('z'), 0, k)                                      # an explicit z would lift it over the rest
            kit = (engine.ENGINE / 'scripts/make-sfx.py').read_text()
            for c in sc['beds'] + sc.get('sfx', []):
                self.assertIn(f"save('{c['name']}'", kit, k)                                    # the local kit makes every sound used
            self.assertEqual(sc['set'], k)

    def test_a_full_frame_template_gets_the_world_sound_not_its_decor(self):
        m = art.scene_visual('map', {'view': {'lon': 11, 'lat': 43, 'span': 6}, 'highlight': ['Italy']}, 'tk-bone', 6.0)
        n = len(m['elements'])
        sets.dress(m, 'florence', 6.0, template='map')
        self.assertEqual(len(m['elements']), n)
        self.assertTrue(m['beds'])
        self.assertEqual(m['elements'][0]['highlight'][0]['n'], 'Italy')          # the story's country, picked out in gold
        self.assertEqual(m['elements'][0]['highlight'][0]['color'], art.GOLD)
        self.assertIn('palette', m['elements'][0])                                   # the atlas look by default
        self.assertNotIn('palette', art.scene_visual('map', {'view': {'lon': 11, 'lat': 43, 'span': 6}, 'plain': True}, 'tk-bone', 6.0)['elements'][0])

    def test_dark_worlds_turn_the_text_light(self):
        self.assertEqual(sets.theme_for('underwater', 'tk-bone'), 'tk-ink')
        self.assertEqual(sets.theme_for(None, 'tk-bone'), 'tk-bone')
        self.assertEqual(art.ink_for(sets.theme_for('radium', 'tk-bone')), art.PAPER)

    def test_the_same_line_gets_the_same_world(self):
        a = sets.dress(art.scene_visual('kinetic_type', {'lines': [{'text': 'x'}]}, 'tk-ink', 5.0), 'underwater', 5.0, seed='l1')
        b = sets.dress(art.scene_visual('kinetic_type', {'lines': [{'text': 'x'}]}, 'tk-ink', 5.0), 'underwater', 5.0, seed='l1')
        self.assertEqual(a, b)

    def test_templates_carry_their_sound_effects(self):
        k = art.scene_visual('kinetic_type', {'lines': [{'text': 'x', 'in': 'slam'}], 'stamp': {'text': 'y', 'at': 1.2}}, 'tk-bone', 5.0)
        self.assertEqual({c['name'] for c in k['sfx']}, {'paper_place', 'stamp'})
        t = art.scene_visual('animated_timeline', {'events': [{'year': '1', 'label': 'a'}, {'year': '2', 'label': 'b'}]}, 'tk-bone', 5.0)
        self.assertEqual(len(t['sfx']), 2)
        r = art.scene_visual('product_reveal', {'asset': 'a', 'desc': 'd', 'name': 'n'}, 'tk-bone', 5.0)
        self.assertEqual([c['name'] for c in r['sfx']], ['whoosh', 'shutter'])
        self.assertTrue(any(e['type'] == 'sparkles' for e in r['elements']))                # the glint on the watch
        short = art.scene_visual('kinetic_type', {'lines': [{'text': 'x'}], 'stamp': {'text': 'y', 'at': 3.0}}, 'tk-bone', 2.0)
        self.assertNotIn('sfx', short)                                                      # never a sound after the scene ends
