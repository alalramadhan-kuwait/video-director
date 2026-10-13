from tests import _guard  # noqa: F401
import tempfile, os, unittest
from director import profiles
from tests.fixtures import PROFILES, EP7

TK = profiles.load(PROFILES / 'timekeeper-luxury-doc.yaml')
DH = profiles.load(PROFILES / 'diabetes-history-sci.yaml')


class TestProfiles(unittest.TestCase):
    def test_profiles_are_separate(self):
        self.assertNotEqual(TK['look']['palette'], DH['look']['palette'])
        self.assertEqual(TK['voice']['final_provider'], 'elevenlabs')
        self.assertEqual(DH['voice']['final_provider'], 'fasih')
        self.assertTrue(set(TK['voice']['library_scopes']).isdisjoint(set(DH['voice']['library_scopes']) - {'global'}))
        self.assertTrue(DH['voice']['voices']['fasih_bram']['publish_block'])

    def test_voice_restrictions(self):
        self.assertEqual(profiles.voice_for(TK, 'abdullah', 'royal-oak')['voice_id'], 'XdoLPWNt7ytn6BtU4FBf')
        with self.assertRaises(PermissionError):
            profiles.voice_for(TK, 'abdullah', 'some-other-film')       # approved per film
        with self.assertRaises(PermissionError):
            profiles.voice_for(TK, 'ali_clone', 'royal-oak')            # needs a per-film authorization
        with self.assertRaises(KeyError):
            profiles.voice_for(DH, 'abdullah', 'ep8')                   # not a Diabetes History voice

    def test_contamination_detected(self):
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, 'storyboard.json')
            with open(bad, 'w', encoding='utf-8') as fh:
                fh.write('{"scenes":[{"endcard":"timekeeper","file":"tk_endcard"}], "palette":{"bg":"#1C3550"}}')
            f = profiles.contamination(DH, [TK, DH], [bad])
            self.assertTrue(any(x['severity'] == 'critical' and x['signature'] == 'tk_endcard' for x in f))

    @unittest.skipUnless((EP7 / 'pl/project.json').exists(), 'episode 7 not present')
    def test_existing_episode7_is_clean_of_time_keeper_style(self):
        files = [EP7 / 'pl/project.json', EP7 / 'mkproj.py'] + sorted((EP7 / 'scenes').glob('*.js'))
        self.assertEqual(profiles.contamination(DH, [TK], files), [])


if __name__ == '__main__':
    unittest.main()
