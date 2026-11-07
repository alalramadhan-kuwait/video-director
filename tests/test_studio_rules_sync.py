"""The studio's rule texts must follow the repo's rules (7 Nov 2026 audit, gap G8: the studio still showed 35–45 shots
a minute and music 5 dB under the voice after the owner had changed both)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / 'skills' / 'reel-master' / 'references'


class StudioRulesFollowTheRepo(unittest.TestCase):
    def setUp(self):
        lib = json.loads((ROOT / 'studio-page' / 'library.json').read_text(encoding='utf-8'))
        self.direction = ' '.join(lib['direction']['rules'])
        self.workflow = json.dumps(lib.get('workflow'), ensure_ascii=False)

    def test_pace_matches_storytelling(self):
        self.assertIn('22–28 shots a minute', (REF / 'storytelling.md').read_text(encoding='utf-8'))
        self.assertIn('22–28 لقطة بالدقيقة', self.direction)
        self.assertNotIn('35–45', self.direction)

    def test_music_bed_matches_ai_film(self):
        self.assertIn('about 20 dB under the voice in the gaps', (REF / 'ai-film.md').read_text(encoding='utf-8'))
        self.assertIn('20 dB', self.direction)
        self.assertNotIn('5 dB تحت الصوت', self.direction)

    def test_final_voice_never_sped_up(self):
        if 'atempo' in self.workflow:
            self.assertRegex(self.workflow, 'الصوت النهائي ما ينسرع|للمراجعة فقط')


if __name__ == '__main__':
    unittest.main()
