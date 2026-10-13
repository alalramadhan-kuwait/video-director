from tests import _guard  # noqa: F401
# Read-only QA adapters: each runs the REAL production checker (node subprocess) on a scratch copy of a small fixture
# built here, and the production tools, their projects and the fixture originals must be byte-identical afterwards.
import json, os, shutil, subprocess, unittest
from pathlib import Path

from director.qa import paper_story, safe_zone
from director.qa._common import sha256_file, tree_digest

ROOT = Path(__file__).resolve().parent.parent
QA = ROOT / 'var/qa'
FIX = QA / 'fixtures'
TMP = QA / 'tmp'
OUT = QA / 'out'
PAPER_TOOL = paper_story.DEFAULT_TOOL
PAPER_SKILL = PAPER_TOOL.parent.parent
PAPER_REPO = PAPER_SKILL.parent.parent.parent
VAE = safe_zone.VAE
SAFE_TOOL = safe_zone.DEFAULT_TOOL
HAVE_NODE = bool(shutil.which('node')) and bool(shutil.which('ffmpeg'))
HAVE_PAPER = HAVE_NODE and PAPER_TOOL.is_file()
HAVE_VAE = HAVE_NODE and SAFE_TOOL.is_file() and (VAE / 'scripts/compose.REFERENCE.html').is_file()

BOTTOM_ZONE = 'أسفل الشاشة (كابشن انستقرام والصوت)'
BELT_ZONE = 'حزام الأسفل الحذر'


# ---------------------------------------------------------------- fixtures (generated, under var/qa/fixtures)
def ff(*args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *map(str, args)], check=True)


def png(path, size, src='testsrc2'):
    path.parent.mkdir(parents=True, exist_ok=True)
    ff('-f', 'lavfi', '-i', f'{src}=s={size}' if src == 'testsrc2' else f'color=c={src}:s={size}', '-frames:v', '1', path)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding='utf-8')


def build_paper_fixtures():
    """story_defect: one known fault per scene. Scene 1 'face': a card over the head of a "person": true cut-out.
    Scene 2 'cut': a print hanging off the right edge, from a 120 px file shown ~4x (soft) that lives OUTSIDE the
    storyboard folder (../shared/), so it only loads if the adapter's copy keeps relative paths valid.
    Scene 3 'misc': a print over another print, and a print on the captions.
    story_clean: same assets laid out with nothing in the way, timed by a silent scene voice clip.
    story_banner: a word and a head under the banner (see the blind-spot test)."""
    d = FIX / 'paper'
    shutil.rmtree(d, ignore_errors=True)
    png(d / 'shared/print_small.png', '120x80')
    for sb in ('defect', 'clean', 'banner', 'die'):
        png(d / sb / 'person.png', '600x800', '0x8a5a3c')
        png(d / sb / 'print.png', '900x600')
    (d / 'clean/voice').mkdir(parents=True)
    ff('-f', 'lavfi', '-i', 'anullsrc=r=22050:cl=mono', '-t', '1.6', d / 'clean/voice/line.wav')
    base = {'width': 720, 'height': 1280, 'fps': 30, 'audio': {'autoSfx': False}}
    write_json(d / 'defect/story.json', {**base, 'scenes': [
        {'id': 'face', 'dur': 2.5, 'theme': 'teal', 'banner': 'ONE', 'transition': 'cut', 'captions': 'a face covered',
         'elements': [{'type': 'cutout', 'src': 'person.png', 'person': True, 'h': 600, 'x': 360, 'y': 960},
                      {'type': 'card', 'w': 320, 'h': 180, 'x': 360, 'y': 420, 'label': 'NOTE'}]},
        {'id': 'cut', 'dur': 2.5, 'theme': 'navy', 'banner': 'TWO', 'transition': 'cut', 'captions': 'print off frame',
         'elements': [{'type': 'image', 'src': '../shared/print_small.png', 'w': 360, 'h': 240, 'x': 700, 'y': 600}]},
        {'id': 'misc', 'dur': 2.5, 'theme': 'rust', 'banner': 'THREE', 'transition': 'cut', 'captions': 'words on the captions here',
         'elements': [{'type': 'image', 'src': 'print.png', 'w': 300, 'h': 200, 'x': 250, 'y': 600},
                      {'type': 'image', 'src': 'print.png', 'w': 300, 'h': 200, 'x': 330, 'y': 640},
                      {'type': 'image', 'src': 'print.png', 'w': 240, 'h': 160, 'x': 360, 'y': 1010}]}]})
    write_json(d / 'clean/story.json', {**base, 'scenes': [
        {'id': 'clean', 'voice': 'voice/line.wav', 'theme': 'teal', 'banner': 'ALL CLEAR', 'transition': 'cut',
         'captions': 'nothing in the way',
         'elements': [{'type': 'cutout', 'src': 'person.png', 'person': True, 'h': 500, 'x': 420, 'y': 940},
                      {'type': 'image', 'src': 'print.png', 'w': 240, 'h': 160, 'x': 160, 'y': 360}]}]})
    write_json(d / 'banner/story.json', {**base, 'scenes': [
        {'id': 'banner', 'dur': 2.5, 'theme': 'rust', 'banner': 'THE BANNER SITS HERE', 'transition': 'cut', 'captions': 'x',
         'elements': [{'type': 'text', 'text': 'HIDDEN', 'size': 80, 'x': 360, 'y': 215},
                      {'type': 'cutout', 'src': 'person.png', 'person': True, 'h': 600, 'x': 360, 'y': 780}]}]})
    write_json(d / 'die/story.json', {**base, 'scenes': [
        {'id': 'die', 'voice': 'voice/missing.wav', 'theme': 'teal', 'banner': 'X', 'elements': []}]})
    return d


def build_vae_fixtures():
    """Minimal video-ad-editor workdirs, set up the way SKILL.md says: compose.html is a copy of
    scripts/compose.REFERENCE.html, plus theme.json, sfx.json (outro), caps.json and a logo.
      clean      full-screen video, captions where the engine puts them  -> passes (reels)
      bottom     studio.json moves the video card to y 1800, so the engine draws the caption card at ~1610-1740,
                 inside the reels bottom zone (y 1620+)                   -> fails
      hook_ok    no compose.html (the checker's hook-only path), first caption at 0.10 s -> passes
      hook_late  no compose.html, first caption at 1.10 s               -> fails
      broken     caps.json is not JSON                                   -> the checker crashes"""
    d = FIX / 'vae'
    shutil.rmtree(d, ignore_errors=True)
    theme = {'bg': '#101828', 'ink': '#F5F7FA', 'acc': '#F2B33D', 'clay': '#C98B18', 'mut': '#98A2B3', 'font': 'Cairo',
             'handle': '@qa_fixture', 'logo': 'logo.png', 'grade': False, 'faceAnchor': 0.30, 'badgeUntil': 0, 'capStyle': 'card',
             'outro': {'l1': 'اختبار', 'l2': 'فحص', 'chips': ['واحد'], 'cta': 'تابع', 'word': 'فحص', 'sub': 'نهاية'}}

    def caps(shift=0.0):
        w = lambda t, s, e: {'t': t, 's': round(s + shift, 3), 'e': round(e + shift, 3), 'hot': False}
        return {'total': 3.0 + shift, 'cards': [
            {'s': round(0.1 + shift, 3), 'e': round(1.4 + shift, 3), 'w': [w('مرحبا', 0.1, 0.6), w('بكم', 0.6, 1.4)]},
            {'s': round(1.5 + shift, 3), 'e': round(2.9 + shift, 3), 'w': [w('هذا', 1.5, 2.0), w('اختبار', 2.0, 2.9)]}]}
    for name in ('clean', 'bottom', 'hook_ok', 'hook_late', 'broken'):
        wd = d / name
        write_json(wd / 'theme.json', theme)
        write_json(wd / 'sfx.json', {'outro': 1.0})
        write_json(wd / 'caps.json', caps(1.0 if name == 'hook_late' else 0.0))
        if name in ('clean', 'bottom', 'broken'):
            shutil.copyfile(VAE / 'scripts/compose.REFERENCE.html', wd / 'compose.html')
            png(wd / 'logo.png', '200x200', '0x222222')
    write_json(d / 'bottom/studio.json', {'scenes': [{'s': 0, 'e': 99, 'm': {'x': 350, 'y': 1800, 'w': 380, 'h': 520, 'r': 32}}]})
    (d / 'broken/caps.json').write_text('{not json', encoding='utf-8')
    return d


def codes(r, *only):
    return [f['code'] for f in r['findings'] if not only or f['code'] in only]


def by_code(r, code):
    return [f for f in r['findings'] if f['code'] == code]


# ---------------------------------------------------------------- module setup: build fixtures, snapshot originals
SNAP = {}


def watched():
    w = {}
    if HAVE_PAPER:
        w['paper-story skill'] = PAPER_SKILL
    if HAVE_VAE:
        w['video-ad-editor scripts'] = VAE / 'scripts'
    for name in ('paper', 'vae'):
        if (FIX / name).is_dir():
            w['fixture ' + name] = FIX / name
    return w


def setUpModule():
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(OUT, ignore_errors=True)
    if HAVE_PAPER:
        build_paper_fixtures()
    if HAVE_VAE:
        build_vae_fixtures()
    for k, p in watched().items():
        SNAP[k] = tree_digest(p)
    if HAVE_VAE:
        SNAP['vae package.json'] = sha256_file(VAE / 'package.json')


class Untouched:
    def assertUntouched(self):
        for k, p in watched().items():
            self.assertEqual(tree_digest(p), SNAP[k], f'{k} changed during the run')
        if HAVE_VAE:
            self.assertEqual(sha256_file(VAE / 'package.json'), SNAP['vae package.json'])
        self.assertEqual([p for p in (FIX / 'vae').rglob('safe.jpg')] if (FIX / 'vae').is_dir() else [], [],
                         'safe.jpg appeared in an original workdir')
        self.assertEqual(sorted(os.listdir(TMP)), [], 'a scratch copy was left behind')


# ---------------------------------------------------------------- paper-story
@unittest.skipUnless(HAVE_PAPER, 'node/ffmpeg or the paper-story checker is not available')
class TestPaperStory(unittest.TestCase, Untouched):
    @classmethod
    def setUpClass(cls):
        cls.defect = paper_story.check(FIX / 'paper/defect/story.json', out_dir=OUT / 'paper-defect', tmp_root=TMP, timeout=180)
        cls.clean = paper_story.check(FIX / 'paper/clean/story.json', out_dir=OUT / 'paper-clean', tmp_root=TMP, timeout=180)
        cls.banner = paper_story.check(FIX / 'paper/banner/story.json', out_dir=OUT / 'paper-banner', tmp_root=TMP, timeout=180)

    def test_defect_storyboard_fails_with_the_right_codes_and_scenes(self):
        r = self.defect
        self.assertEqual(r['exit_code'], 1, r['raw_stderr'])
        self.assertFalse(r['passed'])
        self.assertTrue(r['ran_on_copy'])
        self.assertEqual(r['tool'], 'paper-story --check')
        self.assertEqual(r['tool_sha256'], sha256_file(PAPER_TOOL))
        self.assertEqual(codes(r, 'TOOL_ERROR', 'PARSE_MISMATCH', 'UNPARSED', 'PAGE_ERROR', 'PLACEHOLDER'), [], r['raw_stdout'])
        got = {(f['code'], f['scene'], f['data']['scene_id']) for f in r['findings']}
        self.assertEqual(got, {('FACE_COVERED', 1, 'face'), ('CUT_BY_FRAME', 2, 'cut'), ('SOFT_IMAGE', 2, 'cut'),
                               ('OVERLAP', 3, 'misc'), ('ON_CAPTIONS', 3, 'misc')})
        face, = by_code(r, 'FACE_COVERED')
        self.assertEqual((face['severity'], face['data']['subject']), ('major', 'card "NOTE"'))
        self.assertGreater(face['data']['pct'], 12)
        self.assertTrue(face['data']['person'].endswith('/fixtures/paper/defect/person.png'),
                        'the person is named by its ORIGINAL path, not the scratch copy: ' + face['data']['person'])
        self.assertLess(face['from'], face['to'])
        cut, = by_code(r, 'CUT_BY_FRAME')
        self.assertIn('print_small.png', cut['detail'])
        self.assertGreater(cut['data']['pct'], 30)
        soft, = by_code(r, 'SOFT_IMAGE')
        self.assertEqual((soft['severity'], soft['data']['file_px']), ('minor', 120))   # the ../shared file did load
        for f in r['findings']:
            self.assertIn(f['raw'], r['raw_stdout'].splitlines())
        self.assertEqual(r['summary'], {'clashes': 1, 'cut': 1, 'overlap_or_captions': 2})
        self.assertTrue((OUT / 'paper-defect/paper_story_check.json').is_file())
        self.assertUntouched()

    def test_clean_storyboard_passes(self):
        r = self.clean
        self.assertEqual(r['exit_code'], 0, r['raw_stdout'] + r['raw_stderr'])
        self.assertTrue(r['passed'])
        self.assertEqual(codes(r), [], r['raw_stdout'] + r['raw_stderr'])
        self.assertEqual(r['summary'], {'clashes': 0, 'cut': 0, 'overlap_or_captions': 0})
        self.assertUntouched()

    def test_render_die_is_a_tool_error(self):
        r = paper_story.check(FIX / 'paper/die/story.json', tmp_root=TMP, timeout=120)
        self.assertEqual(r['exit_code'], 1)                 # render.mjs dies with exit 1, the same code as "faults found"
        self.assertFalse(r['passed'])
        err, = by_code(r, 'TOOL_ERROR')
        self.assertIn('scene voice not found', err['detail'])
        self.assertIn('/fixtures/paper/die/voice/missing.wav', err['detail'])
        self.assertUntouched()

    def test_missing_checker_or_storyboard_is_a_tool_error_without_running(self):
        r = paper_story.check(FIX / 'paper/clean/story.json', tool_path=FIX / 'nope.mjs', tmp_root=TMP)
        self.assertEqual((r['exit_code'], r['passed'], codes(r)), (None, False, ['TOOL_ERROR']))
        r = paper_story.check(FIX / 'paper/nope.json', tmp_root=TMP)
        self.assertEqual((r['exit_code'], r['passed'], codes(r)), (None, False, ['TOOL_ERROR']))

    @unittest.expectedFailure
    def test_banner_blind_spot_in_the_production_checker(self):
        """KNOWN GAP in the production checker, not in the adapter: paper.css gives .banner width:0;height:0, so the
        banner's getBoundingClientRect() is 0x0 and neither "X is P% under the banner" nor "banner ... covers P% of
        the head of ..." can ever be printed. A word and a head placed squarely under the banner pass. This test
        expects them to be reported; it will turn into an unexpected success once the checker is fixed."""
        self.assertIn('UNDER_BANNER', codes(self.banner), self.banner['raw_stdout'])

    def test_banner_fixture_ran_cleanly(self):
        """The run behind the blind-spot test itself worked (so the expected failure above is the checker's gap)."""
        r = self.banner
        self.assertIn(r['exit_code'], (0, 1))
        self.assertEqual(codes(r, 'TOOL_ERROR', 'PARSE_MISMATCH', 'UNPARSED', 'PAGE_ERROR'), [], r['raw_stdout'] + r['raw_stderr'])
        self.assertEqual(r['summary'].get('clashes'), 0)
        self.assertUntouched()


class TestPaperStoryParser(unittest.TestCase):
    """Pure parsing. The sentences are built from render.mjs's own format strings (see its `if (opt.check)` block);
    UNDER_BANNER is only testable this way because the checker cannot currently print it (blind spot above)."""

    def test_every_sentence_maps_to_a_code(self):
        out = '\n'.join([
            'scene 2  0.7-2.3s  text "SALE" is 40% under the banner',
            'scene 1  0.7-2.5s  banner "ONE" covers 33% of the head of file:///M/person.png',
            '1 clash(es)',
            'scene 3  1.0-2.0s  image "a.png" is 12% outside the frame',
            '1 cut by the frame',
            'scene 3  1.0-2.0s  image "b.png" covers the label of image "a.png" (18%)',
            'scene 4  1.0-2.0s  card "x" sits on the captions (30% of a word)',
            '2 overlap(s) or picture(s) on the captions',
            'note: scene 4  image "c.png" is shown at 210% of its file (300px wide): it will look soft',
            'something new the checker started printing'])
        err = 'placeholders still showing (1): ep1_boulder_01\npage error: boom\nrender: could not launch Chromium: x'
        f, summary = paper_story.parse(out, err, scenes=[{'id': 'a'}, {'id': 'b'}], unmap=lambda s: s.replace('/M/', '/ORIG/'))
        self.assertEqual([x['code'] for x in f], ['UNDER_BANNER', 'FACE_COVERED', 'CUT_BY_FRAME', 'OVERLAP', 'ON_CAPTIONS',
                                                  'SOFT_IMAGE', 'UNPARSED', 'PLACEHOLDER', 'PAGE_ERROR', 'TOOL_ERROR'])
        self.assertEqual(summary, {'clashes': 1, 'cut': 1, 'overlap_or_captions': 2})
        ub = f[0]
        self.assertEqual((ub['scene'], ub['from'], ub['to'], ub['data']['scene_id'], ub['data']['pct']), (2, 0.7, 2.3, 'b', 40))
        self.assertEqual(f[1]['data']['person'], 'file:///ORIG/person.png')
        self.assertEqual(f[1]['data']['subject'], 'banner "ONE"')
        self.assertEqual(f[6]['severity'], 'info')
        self.assertEqual(f[6]['raw'], 'something new the checker started printing')
        self.assertEqual(f[-1]['severity'], 'critical')

    def test_totals_that_disagree_with_the_parse_are_flagged(self):
        f, summary = paper_story.parse('2 clash(es)\nnothing cut by the frame\nno print over another, nothing on the captions', '')
        self.assertEqual([x['code'] for x in paper_story._consistency(f, summary, 1)], ['PARSE_MISMATCH', 'PARSE_MISMATCH'])


# ---------------------------------------------------------------- video-ad-editor 08_safe_check
@unittest.skipUnless(HAVE_VAE, 'node/ffmpeg or the video-ad-editor checker is not available')
class TestSafeZone(unittest.TestCase, Untouched):
    @classmethod
    def setUpClass(cls):
        cls.clean = safe_zone.check(FIX / 'vae/clean', out_dir=OUT / 'vae-clean', tmp_root=TMP, timeout=180)
        cls.bottom = safe_zone.check(FIX / 'vae/bottom', out_dir=OUT / 'vae-bottom', tmp_root=TMP, timeout=180)

    def test_clean_workdir_passes(self):
        r = self.clean
        self.assertEqual(r['exit_code'], 0, r['raw_stdout'] + r['raw_stderr'])
        self.assertTrue(r['passed'])
        self.assertEqual(r['tool_sha256'], sha256_file(SAFE_TOOL))
        self.assertEqual(codes(r, 'HOOK_LATE', 'ZONE_HARD', 'ZONE_SOFT', 'TOOL_ERROR', 'UNPARSED', 'PARSE_MISMATCH', 'COMPOSE_ERROR'), [],
                         r['raw_stdout'] + r['raw_stderr'])
        s = r['summary']
        self.assertEqual((s['platform'], s['pixel_check'], s['verdict'], s['hook']['first_caption_s']), ('reels', True, 'pass', 0.1))
        self.assertEqual([z['status'] for z in s['zones']], ['ok'] * 4)
        self.assertIsNone(r['safe_jpg'])
        self.assertFalse((OUT / 'vae-clean/safe.jpg').exists())
        self.assertUntouched()

    def test_caption_in_the_bottom_zone_fails_and_safe_jpg_goes_to_out_dir_only(self):
        r = self.bottom
        self.assertEqual(r['exit_code'], 3, r['raw_stdout'] + r['raw_stderr'])
        self.assertFalse(r['passed'])
        hard = by_code(r, 'ZONE_HARD')
        self.assertEqual([f['data']['zone'] for f in hard], [BOTTOM_ZONE])
        self.assertEqual(hard[0]['severity'], 'critical')
        self.assertGreater(hard[0]['data']['ink_pct'], hard[0]['data']['allowed_pct'])
        self.assertEqual(codes(r, 'TOOL_ERROR', 'UNPARSED', 'PARSE_MISMATCH', 'HOOK_LATE'), [])
        self.assertEqual(r['summary']['verdict'], 'fail')
        jpg = OUT / 'vae-bottom/safe.jpg'
        self.assertEqual(r['safe_jpg'], str(jpg))
        self.assertEqual(jpg.read_bytes()[:3], b'\xff\xd8\xff')
        self.assertEqual(r['summary']['shot']['printed_path'], str(jpg))   # the copy's path is never reported
        self.assertFalse((FIX / 'vae/bottom/safe.jpg').exists())
        self.assertUntouched()

    def test_shot_false_writes_no_safe_jpg(self):
        r = safe_zone.check(FIX / 'vae/bottom', shot=False, out_dir=OUT / 'vae-noshot', tmp_root=TMP, timeout=180)
        self.assertEqual((r['exit_code'], r['safe_jpg']), (3, None))
        self.assertFalse((OUT / 'vae-noshot/safe.jpg').exists())
        self.assertUntouched()

    def test_platform_goes_into_the_copy_only(self):
        r = safe_zone.check(FIX / 'vae/clean', platform='tiktok', out_dir=OUT / 'vae-tiktok', tmp_root=TMP, timeout=180)
        self.assertEqual(r['summary']['platform'], 'tiktok')
        self.assertEqual(r['exit_code'], 0)
        self.assertTrue(r['passed'])
        # tiktok's caution belt starts at y 1480, so the default caption card (bottom edge ~1460) grazes it: a soft warning
        self.assertEqual([f['data']['zone'] for f in by_code(r, 'ZONE_SOFT')], [BELT_ZONE])
        self.assertFalse((FIX / 'vae/clean/safe.json').exists())
        self.assertUntouched()

    def test_unknown_platform_is_flagged(self):
        r = safe_zone.check(FIX / 'vae/clean', platform='myspace', out_dir=OUT / 'vae-myspace', tmp_root=TMP, timeout=180)
        self.assertEqual(codes(r, 'UNKNOWN_PLATFORM'), ['UNKNOWN_PLATFORM'])
        self.assertUntouched()

    def test_hook_only_path(self):
        ok = safe_zone.check(FIX / 'vae/hook_ok', out_dir=OUT / 'vae-hook-ok', tmp_root=TMP, timeout=60)
        late = safe_zone.check(FIX / 'vae/hook_late', out_dir=OUT / 'vae-hook-late', tmp_root=TMP, timeout=60)
        self.assertEqual((ok['exit_code'], ok['passed'], codes(ok)), (0, True, ['NO_PIXEL_CHECK']))
        self.assertEqual((late['exit_code'], late['passed']), (3, False))
        self.assertEqual(codes(late), ['HOOK_LATE', 'NO_PIXEL_CHECK'])
        f, = by_code(late, 'HOOK_LATE')
        self.assertEqual((f['data']['first_caption_s'], f['data']['max_s']), (1.1, 0.5))
        self.assertFalse(late['summary']['pixel_check'])
        self.assertUntouched()

    def test_checker_crash_and_bad_input_are_tool_errors(self):
        r = safe_zone.check(FIX / 'vae/broken', out_dir=OUT / 'vae-broken', tmp_root=TMP, timeout=60)
        self.assertEqual((r['exit_code'], r['passed']), (1, False))
        self.assertIn('TOOL_ERROR', codes(r))
        self.assertIn('SyntaxError', r['raw_stderr'])
        r = safe_zone.check(FIX / 'vae', out_dir=OUT / 'vae-nocaps', tmp_root=TMP)      # no sfx.json/caps.json: never runs
        self.assertEqual((r['exit_code'], codes(r)), (None, ['TOOL_ERROR']))
        self.assertUntouched()


class TestSafeZoneParser(unittest.TestCase):
    def test_soft_zone_and_unknown_lines(self):
        out = ('— الهوك —\n✅ أول كابشن عند 0.10 ثانية\n'
               '⚠️  حزام الأسفل الحذر: 3.01٪ من المساحة عند 1.75ث (المسموح 1.00٪)\nsomething new')
        f, s = safe_zone.parse(out, '[compose] PAGEERR x is not defined\nweird')
        self.assertEqual([x['code'] for x in f], ['ZONE_SOFT', 'UNPARSED', 'COMPOSE_ERROR', 'UNPARSED'])
        self.assertEqual((f[0]['severity'], f[0]['data']['ink_pct'], f[0]['from']), ('minor', 3.01, 1.75))
        self.assertEqual(s['zones'][0]['status'], 'soft_warn')
        self.assertEqual([x['code'] for x in safe_zone._consistency(f, s, 3)], ['PARSE_MISMATCH'])


# ---------------------------------------------------------------- real material (read-only, optional)
REAL_OK = [PAPER_SKILL / 'examples/demo.json', PAPER_REPO / 'video/ask-mohammed-reel/story-fahed.json']
REAL_MISSING_MEDIA = PAPER_REPO / 'video/success-story/story.json'


@unittest.skipUnless(HAVE_PAPER and all(p.is_file() for p in REAL_OK), 'the paper-story clone is not here')
class TestRealPaperStoryboards(unittest.TestCase, Untouched):
    def test_real_storyboards_read_only(self):
        repo_before = tree_digest(PAPER_REPO / 'video') | {'public/icon-512.png': sha256_file(PAPER_REPO / 'public/icon-512.png')}
        for sb in REAL_OK:
            with self.subTest(sb.name):
                r = paper_story.check(sb, out_dir=OUT / ('real-' + sb.stem), tmp_root=TMP, timeout=300)
                self.assertEqual((r['exit_code'], r['passed']), (0, True), r['raw_stdout'] + r['raw_stderr'])
                self.assertEqual(codes(r, 'TOOL_ERROR', 'PARSE_MISMATCH', 'PAGE_ERROR', 'UNPARSED'), [])
        r = paper_story.check(REAL_MISSING_MEDIA, out_dir=OUT / 'real-success-story', tmp_root=TMP, timeout=300)
        if not (REAL_MISSING_MEDIA.parent / 'voice/clips/1.wav').exists():     # the success-story media is not in the clone
            self.assertFalse(r['passed'])
            self.assertIn('scene voice not found', by_code(r, 'TOOL_ERROR')[0]['detail'])
        after = tree_digest(PAPER_REPO / 'video') | {'public/icon-512.png': sha256_file(PAPER_REPO / 'public/icon-512.png')}
        self.assertEqual(after, repo_before)
        self.assertUntouched()


if __name__ == '__main__':
    unittest.main()
