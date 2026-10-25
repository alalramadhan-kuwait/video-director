"""The independent critic's pack and ledger (director/critic.py)."""
from tests import _guard  # noqa: F401
import json, shutil, subprocess, tempfile, unittest
from pathlib import Path

from director import critic


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg not available')
class TestCritic(unittest.TestCase):
    def _film(self, d: Path):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=size=180x320:rate=15:duration=6', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=6', '-shortest', '-c:v', 'libx264', '-c:a', 'aac', str(d / 'film.mp4')], check=True)
        (d / 'film.json').write_text(json.dumps({'scenes': [{'id': 'l1', 'dur': 2.5}, {'id': 'l2', 'dur': 2.0}, {'dur': 1.5}]}))
        (d / 'report.json').write_text(json.dumps({'platform': 'Instagram Reels', 'quality': ['scene 2  3.0-3.0s  «x» is hard to read'],
                                                   'lines': [{'id': 'l1', 'heard': 'كلام', 'template': 'archive_photo'}]}))

    def test_a_pack_has_the_film_the_cuts_the_numbers_and_a_brief(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); self._film(d)
            rd = critic.pack(d, 'a test film')
            self.assertEqual(rd.name, 'round-1')
            self.assertTrue((rd / 'sheet-1.jpg').is_file()); self.assertTrue((rd / 'cuts-1.jpg').is_file())
            self.assertFalse((rd / '_f').exists())                                   # no loose frames left behind
            m = json.loads((rd / 'measures.json').read_text())
            self.assertEqual([s['start'] for s in m['scenes']], [0, 2.5, 4.5])
            self.assertEqual(m['scenes'][0]['narration'], 'كلام'); self.assertEqual(m['scenes'][2]['template'], 'end card')
            self.assertIsNotNone(m['integrated_lufs'])
            b = (rd / 'brief.md').read_text()
            self.assertIn('a test film', b); self.assertIn('findings.json', b); self.assertNotIn('previous round', b)

    def test_the_ledger_carries_problems_into_the_next_brief(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d); self._film(d)
            r1 = critic.pack(d)
            (r1 / 'findings.json').write_text(json.dumps({'verdict': 'one more pass', 'problems': [
                {'id': 'R1-1', 'rank': 1, 'at': '3.0s', 'scene': 2, 'severity': 'high', 'what': 'the card hides the face', 'why': '', 'fix': ''}]}))
            e = critic.record(d, r1, changed='')
            self.assertEqual((e['verdict'], e['numbers']['quality']), ('one more pass', 1))
            r2 = critic.pack(d)
            self.assertEqual(r2.name, 'round-2')
            b = (r2 / 'brief.md').read_text()
            self.assertIn('R1-1: 3.0s — the card hides the face', b)
            self.assertIn('Do not trust that anything was fixed', b)


if __name__ == '__main__':
    unittest.main()
