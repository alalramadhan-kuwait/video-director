from tests import _guard  # noqa: F401
import ast, json, os, subprocess, tempfile, unittest
from pathlib import Path
from director.art import review
from director import profiles
from tests.fixtures import PROFILES

ROOT = Path(__file__).resolve().parent.parent
TK = profiles.load(PROFILES / 'timekeeper-luxury-doc.yaml')
DH = profiles.load(PROFILES / 'diabetes-history-sci.yaml')


def synthetic(path, w=1080, h=1920, navy='0x1C3550'):
    """8 s: moving 0–2, frozen navy 2–5.5, black 5.5–6.5, moving 6.5–8, with a -20 dB tone."""
    f = (f"testsrc2=s={w}x{h}:r=30:d=2[a];color=c={navy}:s={w}x{h}:r=30:d=3.5[b];color=c=black:s={w}x{h}:r=30:d=1[c];"
         f"testsrc2=s={w}x{h}:r=30:d=1.5[d];[a][b][c][d]concat=n=4:v=1:a=0[v]")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-filter_complex', f, '-f', 'lavfi', '-i', 'sine=f=440:d=8',
                    '-map', '[v]', '-map', '0:a', '-af', 'volume=0.1', '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                    '-shortest', str(path)], check=True)


class TestReviewer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.video = Path(cls.tmp.name) / 'synthetic.mp4'
        synthetic(cls.video)
        cls.before = cls.video.stat().st_mtime_ns
        timeline = {'scenes': [{'id': 's1', 'start': 0, 'end': 2}, {'id': 's2', 'start': 2, 'end': 5.5},
                               {'id': 's3', 'start': 5.5, 'end': 6.5}, {'id': 's4', 'start': 6.5, 'end': 8}]}
        cls.pack = review.build_pack(cls.video, Path(cls.tmp.name) / 'pack', timeline)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_pack_has_real_evidence(self):
        out = Path(self.tmp.name) / 'pack'
        self.assertTrue((out / 'pack.json').exists() and (out / self.pack['contact']).exists())
        for s in self.pack['scenes']:
            for p in list(s['stills'].values()) + [s['strip']]:
                self.assertGreater((out / p).stat().st_size, 1000, p)
        self.assertEqual(self.video.stat().st_mtime_ns, self.before)          # the video is only read

    def test_contact_sheet_has_one_filled_tile_per_scene(self):
        import numpy as np, subprocess
        sheet = Path(self.tmp.name) / 'pack' / self.pack['contact']
        w, h = map(int, subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0',
                                        str(sheet)], capture_output=True, text=True).stdout.split(','))
        g = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', str(sheet), '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                                         capture_output=True).stdout, dtype=np.uint8).reshape(h, w)
        tw = (w + 4) // 8 - 4
        n = len(self.pack['scenes'])
        rows = (n + 7) // 8; th = (h + 4) // rows - 4
        filled = [abs(float(g[r*(th+4):r*(th+4)+th, c*(tw+4):c*(tw+4)+tw].mean()) - 32) > 3
                  or g[r*(th+4):r*(th+4)+th, c*(tw+4):c*(tw+4)+tw].std() > 3
                  for r in range(rows) for c in range(8)]
        self.assertEqual(sum(filled[:n]), n)                   # every scene has its tile (the M3 sheet sampled only 8)
        self.assertEqual(sum(filled[n:]), 0)

    def test_measures_black_and_frozen(self):
        m = self.pack['measured']
        self.assertTrue(any(5.3 < a < 5.8 for a, b in m['black']), m['black'])
        self.assertTrue(any(1.8 < a < 2.4 and b - a >= 3.0 for a, b in m['frozen']), m['frozen'])

    def test_technical_findings(self):
        f = review.technical_pass(self.pack, 'tiktok', DH, [TK, DH])
        codes = {x['code']: x for x in f}
        self.assertIn('BLACK_STRETCH', codes)
        self.assertEqual(codes['BLACK_STRETCH']['scene'], 's3')
        self.assertIn('STATIC_STRETCH', codes)
        self.assertEqual(codes['STATIC_STRETCH']['scene'], 's2')
        self.assertNotIn('WRONG_SIZE', codes)
        self.assertNotIn('STATIC_OPENING', codes)                             # it moves from frame 1
        self.assertIn('WRONG_SIZE', {x['code'] for x in review.technical_pass(self.pack, 'youtube', DH, [TK, DH])})

    def test_palette_contamination_is_detected_both_ways(self):
        # navy (#1C3550) dominates s2: that is Diabetes History's colour. Judged as a Time Keeper film it is foreign.
        tk_view = {x['code'] for x in review.technical_pass(self.pack, 'tiktok', TK, [TK, DH])}
        dh_view = {x['code'] for x in review.technical_pass(self.pack, 'tiktok', DH, [TK, DH])}
        self.assertIn('PALETTE_CONTAMINATION', tk_view)
        self.assertNotIn('PALETTE_CONTAMINATION', dh_view)

    def test_review_packets_cover_all_stages(self):
        for st in review.STAGES:
            p = review.review_packet(self.pack, st, DH)
            self.assertTrue(p['questions'])
            self.assertEqual(len(p['evidence']['scenes']), 4)

    def test_finding_validation(self):
        with self.assertRaises(AssertionError):
            review.finding('X', 'catastrophic', 'bad severity')


class TestIsolation(unittest.TestCase):
    def imports(self, path):
        tree = ast.parse(Path(path).read_text(encoding='utf-8'))
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import): names |= {a.name for a in n.names}
            if isinstance(n, ast.ImportFrom): names.add((n.module or '') + ('.' if n.level else ''))
        return names

    def test_reviewer_cannot_reach_director_voice_or_gateway(self):
        names = self.imports(ROOT / 'director/art/review.py')
        self.assertFalse(any('voice' in n or 'gateway' in n or 'selector' in n for n in names), names)

    def test_no_art_module_can_reach_paid_generation(self):
        for p in (ROOT / 'director/art').glob('*.py'):
            src = p.read_text(encoding='utf-8')
            self.assertNotIn('gateway', src.replace('paid gateway', '').replace('the gateway', ''), p.name)
            self.assertNotIn('api.elevenlabs', src, p.name)


if __name__ == '__main__':
    unittest.main()
