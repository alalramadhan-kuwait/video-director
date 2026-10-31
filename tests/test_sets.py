"""Story worlds dress any template without covering it; their sounds exist; templates carry their own sound effects."""
from tests import _guard  # noqa: F401
import json, re, unittest

from director.studio import art, drawn, engine, sets


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

    NEW = ('auction_room', 'paris_rail', 'home_70s', 'home_70s_driver', 'paris_atelier', 'jura', 'basel_fair', 'swiss_atelier', 'waiting_years')

    def _dressed(self, k, dur=8.0, seed='l1'):
        base = art.scene_visual('kinetic_type', {'lines': [{'text': 'x'}]}, sets.theme_for(k, 'tk-bone'), dur)
        own = len(base['elements'])
        sc = sets.dress(base, k, dur, seed=seed, template='kinetic_type')
        return sc, [e for e in sc['elements'] if e.get('behind')], sc['elements'][len([e for e in sc['elements'] if e.get('behind')]) + own:]

    def test_the_new_worlds_are_drawn_in_depth_with_a_bed_and_keep_the_middle_clear(self):
        for k in self.NEW:
            sc, back, front = self._dressed(k)
            self.assertGreaterEqual(len(back), 5, k)                                          # a room, not a colour
            self.assertGreaterEqual(len({e.get('depth') for e in back}), 3, k)                 # layers that move apart with the camera
            self.assertTrue(sc['beds'], k)
            self.assertIn(k, sets.NAME_AR)
            for e in back + front:
                self.assertEqual(e['type'], 'svg', k)                                          # drawn in code: no image, nothing generated
                self.assertNotIn('<image', e['svg'], k)
            for e in front:                                                                    # over the template: below the middle or at the edges
                xs = [v for _, v, *_ in e['x']] if isinstance(e['x'], list) else [e['x']]
                ys = [v for _, v, *_ in e['y']] if isinstance(e['y'], list) else [e['y']]
                k_ = e.get('scale', 1) if not isinstance(e.get('scale', 1), list) else 1
                top = min(ys) - e['h'] * k_ / 2
                left, right = min(xs) - e['w'] / 2, max(xs) + e['w'] / 2
                self.assertTrue(top >= 860 or right <= 110 or left >= 610, f'{k}: front decor at x {left:.0f}..{right:.0f}, top {top:.0f}')
                self.assertTrue(e.get('crop') and e.get('underCaptions'), k)

    def test_every_gradient_id_is_new_in_each_scene(self):
        ids = []
        for k in self.NEW:
            for seed in ('a', 'b'):
                for e in self._dressed(k, seed=seed)[0]['elements']:
                    ids += re.findall(r'id="([^"]+)"', e.get('svg', ''))
        self.assertEqual(len(ids), len(set(ids)))

    def test_the_paddles_rise_one_after_another(self):
        sc, back, _ = self._dressed('auction_room')
        rises = sorted(e['y'][1][0] for e in back if isinstance(e.get('y'), list) and len(e['y']) == 5)
        self.assertEqual(rises[:3], [1.0, 1.6, 2.2])

    def test_the_train_crosses_on_the_far_line_above_the_captions_and_the_lights_come_on(self):
        dur = 6.0
        _, back, front = self._dressed('paris_rail', dur=dur)
        train = max(back, key=lambda e: e['w'])
        self.assertNotIn(train, front)                                               # behind the boy, on the far line
        half = train['w'] * train.get('scale', 1) / 2
        self.assertGreater(train['x'][0][1], 720 + half)                            # starts off the frame on the right
        self.assertLess(train['x'][-1][1], -half)                                   # and leaves it on the left
        self.assertLessEqual(train['y'] + train['h'] * train.get('scale', 1) / 2, 1004)   # above the captions (captionY 1004)
        (_, x0), (t0, _), (t1, x1, _) = train['x']
        mid = t0 + (t1 - t0) * (x0 - 360) / (x0 - x1)                               # mid-frame on «القطارات»
        self.assertAlmostEqual(mid, .73 * dur + .6, delta=.2)
        self.assertLess(mid, dur)
        _, back, _ = self._dressed('jura', dur=6.0)
        lights = [e for e in back if isinstance(e.get('opacity'), list) and e['opacity'][0][1] == 0 and len(e['opacity']) == 3]
        self.assertGreaterEqual(len(lights), 6)
        self.assertGreater(len({e['opacity'][1][0] for e in lights}), 3)            # one by one, not all at once

    def test_the_driver_walks_in_from_the_side_and_stops_at_the_edge(self):
        self.assertIn('rail_driver', drawn.DRESS)
        svg, w, h = drawn.person('rail_driver', uid='rd')
        self.assertTrue(svg.startswith('<svg') and (w, h) == (300, 900))
        el = drawn.walk_in('rail_driver', uid='rd', at=.5, walk=2.0)
        self.assertEqual(el['type'], 'svg')
        self.assertGreater(el['x'][0][1], 720 + el['w'] / 2)                         # off the frame until he walks in
        self.assertEqual(el['x'][-1][0], 2.5)
        self.assertGreaterEqual(el['x'][-1][1] - el['w'] / 2, 500)                  # he stops at the side: the middle stays clear
        sc, back, _ = self._dressed('home_70s_driver')
        self.assertTrue(any(e.get('svg', '').count('feDropShadow') and isinstance(e.get('x'), list) for e in back))
        self.assertEqual(sets.theme_for('home_70s', 'tk-ink'), sets.theme_for('home_70s_driver', 'tk-ink'))

    def test_the_father_stops_whole_in_the_frame_and_a_crate_of_gears_lands(self):
        dur = 4.0
        sc, back, front = self._dressed('home_70s_driver', dur=dur)
        father = next(e for e in back if 'feDropShadow' in e.get('svg', '') and isinstance(e.get('x'), list))
        stop = father['x'][-1][1]
        self.assertLess(stop, 622)                                                   # further in than before
        self.assertGreaterEqual(stop - father['w'] / 2, 0); self.assertLessEqual(stop + father['w'] / 2, 720)   # whole across
        self.assertGreaterEqual(father['y'] - father['h'] / 2, 0); self.assertLessEqual(father['y'] + father['h'] / 2, 1280)  # and top to bottom
        crate = next(e for e in front if '<polygon' in e['svg'] and isinstance(e.get('y'), list))
        land, y = crate['y'][-1][:2]
        self.assertGreater(land, father['x'][-1][0])                                 # after he stops
        self.assertLess(land, dur)
        self.assertTrue(1005 < y + crate['h'] / 2 < 1155, y)                          # on the tabletop
        self.assertEqual(crate['svg'].count('<circle'), crate['svg'].count('<polygon'))   # gears and their holes only: no dial

    @staticmethod
    def _faces(svg):                                                                 # a round face: any circle bigger than a hole or a nail
        return [r for r in re.findall(r'<circle[^>]*\br="([\d.]+)"[^>]*>', svg)
                if float(r) > 8] if svg else []

    def test_the_new_worlds_draw_no_watch_and_no_dial(self):
        self.assertIn('swiss_atelier', sets.SETS); self.assertIn('waiting_years', sets.SETS)
        self.assertEqual(sets.NAME_AR['swiss_atelier'], 'ورشته في سويسرا')
        self.assertEqual(sets.NAME_AR['waiting_years'], 'سنوات الانتظار')
        for k in ('swiss_atelier', 'waiting_years'):
            for dur in (1.0, 4.0, 8.0):
                w = sets.SETS[k](dur, __import__('random').Random(k))
                self.assertTrue(w['elements'] and w['beds'], k)
                for e in w['elements']:
                    self.assertEqual(e['type'], 'svg', k)
                    self.assertNotRegex(e['svg'].lower(), r'\bwatch|\bdial\b|clock|<image', k)
        import random
        cal = sets.waiting_years(8.0, random.Random(1))['elements']
        self.assertEqual([f for e in cal for f in self._faces(e['svg']) if 'url(#' not in e['svg']], [])   # no clock face
        years = [int(y) for e in cal for y in re.findall(r'>(\d{4})</text>', e['svg'])]
        self.assertEqual(sorted(years), list(range(2003, 2011)))
        falls = [e for e in cal if re.search(r'>\d{4}</text>', e['svg']) and isinstance(e['y'], list)]
        self.assertEqual(len(falls), 7)                                              # every year falls but the last
        last = next(e for e in cal if '>2010</text>' in e['svg'])
        self.assertNotIn('rot', last); self.assertEqual(last['y'], 400)              # 2010 stays, straight, clear of the app's buttons
        self.assertLess(max(e['y'][2][0] for e in falls), 8.0)
        base = sets.paris_atelier(8.0, random.Random(2))['elements']
        swiss = sets.swiss_atelier(8.0, random.Random(2))['elements']
        self.assertEqual(len(swiss), len(base) + 5)                                 # the Jura in the window, and four makers
        self.assertEqual(self._faces(swiss[2]['svg']), [])
        makers = swiss[-4:]
        self.assertTrue(all('feDropShadow' in e['svg'] and e['opacity'][-1][1] < 1 for e in makers))   # drawn, faceless, a little faded
        self.assertEqual(sorted({e['y'][1][0] for e in makers})[0], round(8.0 * .45, 2))                 # rising from .45 of the scene

    def test_a_sound_the_kit_does_not_make_yet_never_stops_a_render(self):
        kit = (engine.ENGINE / 'scripts/make-sfx.py').read_text()
        sc, _, _ = self._dressed('paris_rail')
        self.assertEqual(sc['beds'][0]['name'], 'train' if "save('train'" in kit else sets.STAND_IN['train'])
        self.assertIsNone(sets.sound('no_such_sound'))
        self.assertEqual(sets.sound('crowd'), 'crowd')

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
        norm = lambda sc: re.sub(r'(bd|glow|wash)\d+', 'id', json.dumps(sc, ensure_ascii=False))   # gradient ids are unique per scene
        self.assertEqual(norm(a), norm(b))

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
