"""Every city flies in from its country, shows its colours and skyline, and has a sound the local kit makes."""
from tests import _guard  # noqa: F401
import json, unittest
import xml.etree.ElementTree as ET

from director.studio import art, cities, engine


class TestCities(unittest.TestCase):
    def test_every_city_has_a_valid_skyline_its_country_and_its_sound(self):
        names = {c['n'] for c in json.loads((engine.ENGINE / 'assets/geo/world.json').read_text())['countries']}
        kit = (engine.ENGINE / 'scripts/make-sfx.py').read_text()
        for k, c in cities.CITIES.items():
            layers = cities.skyline(k)
            self.assertEqual(len(layers), 3, k)
            for svg in layers: ET.fromstring(svg)                                   # well-formed SVG
            self.assertIn(c['country'], names, k)                                  # the map can highlight it
            self.assertIn(f"save('{c['bed']}'", kit, k)

    def test_the_zoom_centres_the_city_before_the_deep_zoom_and_the_skyline_rises_after(self):
        sc = art.scene_visual('city_zoom', {'city': 'geneva', 'sub': 'سويسرا'}, 'tk-bone', 9.0)
        m = sc['elements'][0]
        (t0, v0), (t1, v1, _), (t2, v2, _) = m['view']
        self.assertEqual((v1['lon'], v1['lat']), (v2['lon'], v2['lat']))           # centred at the half-way key
        self.assertTrue(v0['span'] > v1['span'] > v2['span'])
        self.assertEqual(m['highlight'][0]['n'], 'Switzerland')
        rises = [e['in']['at'] for e in sc['elements'] if e.get('anchor') == 'b']
        self.assertEqual(len(rises), 3); self.assertEqual(rises, sorted(rises)); self.assertGreater(rises[0], t2)
        self.assertTrue(sc['beds'][0]['from'] >= t2)                                # the city sounds once we are there
        self.assertTrue(art.production_ready('city_zoom'))

    def test_gradient_ids_are_unique_across_scenes(self):
        a = art.scene_visual('city_zoom', {'city': 'kuwait'}, 'tk-bone', 8.0)
        b = art.scene_visual('city_zoom', {'city': 'kuwait'}, 'tk-bone', 8.0)
        wash = lambda sc: next(e['svg'] for e in sc['elements'] if e.get('z') == 20)
        self.assertNotEqual(wash(a), wash(b))
