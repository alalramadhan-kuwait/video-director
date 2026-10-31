"""Real sounds from Openverse: CC0 or CC BY only (never NC/ND/SA), CC0 first; retried when Openverse is busy and a plain
message when it is down; the source page's licence re-checked; cached outside git, levelled like the procedural kit,
with a licence record; a film falls back to the procedural kit and credits every found sound it plays. No network:
every call is mocked (tests/_guard.py blocks the rest)."""
from tests import _guard  # noqa: F401
import io, json, os, shutil, tempfile, unittest, urllib.error, wave
from pathlib import Path
from unittest import mock

import numpy as np
import yaml

from director.copilot import sounds
from director.studio import mix

FILE_URL = 'https://cdn.freesound.org/previews/1/1_1-hq.mp3'


def wav_bytes(seconds=1.5, lead=0.4, amp=0.3, sr=44100) -> bytes:
    """A decaying knock after `lead` s of silence, as a 16-bit mono WAV."""
    t = np.arange(int(sr * seconds)) / sr
    x = amp * np.sin(2 * np.pi * 300 * t) * np.exp(-6 * t)
    x = np.concatenate([np.zeros(int(sr * lead)), x, np.zeros(int(sr * .3))])
    b = io.BytesIO()
    with wave.open(b, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype('<i2').tobytes())
    return b.getvalue()


def result(i, lic='cc0', ver='1.0', title='gavel on wood', dur=2000, url=None, **kw):
    deed = url or ('https://creativecommons.org/publicdomain/zero/1.0/' if lic == 'cc0' else f'https://creativecommons.org/licenses/{lic}/{ver}/')
    return {'id': f'id-{i}', 'title': title, 'creator': f'maker{i}', 'license': lic, 'license_version': ver,
            'license_url': deed, 'foreign_landing_url': f'https://freesound.org/people/maker{i}/sounds/{i}/', 'url': FILE_URL,
            'source': 'freesound', 'filetype': 'mp3', 'duration': dur, 'tags': [{'name': 'gavel'}],
            'attribution': f'"{title}" by maker{i} is licensed under {lic}', **kw}


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.env = {k: os.environ.get(k) for k in ('VD_SFX_CACHE', 'VD_SOUNDS', 'VD_EARSHOT')}
        os.environ['VD_SFX_CACHE'] = str(self.d / 'cache'); os.environ.pop('VD_SOUNDS', None)
        os.environ['VD_EARSHOT'] = str(self.d / 'no-earshot')               # never the developer's own earshot in a test
        p = mock.patch('time.sleep'); p.start(); self.addCleanup(p.stop)
        sounds._last[0] = 0.0

    def tearDown(self):
        for k, v in self.env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        shutil.rmtree(self.d, ignore_errors=True)

    def web(self, api=None, page='<a href="https://creativecommons.org/publicdomain/zero/1.0/">CC0</a>', audio=None):
        """Mocks every request: Openverse answers `api(params)`, the page answers `page`, the file is a WAV."""
        audio = audio or wav_bytes()
        seen = []

        def http(url, **kw):
            seen.append(url)
            if url.startswith(sounds.API):
                from urllib.parse import urlsplit, parse_qs
                q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
                r = api(q, url) if api else {'results': []}
                if isinstance(r, Exception): raise r
                return json.dumps(r).encode()
            if url == FILE_URL: return audio
            if isinstance(page, Exception): raise page
            return page.encode()
        p = mock.patch.object(sounds, '_http', side_effect=http); p.start(); self.addCleanup(p.stop)
        return seen


class TestLicences(Base):
    def test_only_cc0_and_cc_by_are_used(self):
        self.assertTrue(sounds.licence_ok(result(1, 'cc0')))
        self.assertTrue(sounds.licence_ok(result(1, 'by', '4.0')))
        for lic in ('by-nc', 'by-nd', 'by-sa', 'by-nc-sa', 'sampling+', 'pdm', 'nc-sampling+'):
            self.assertFalse(sounds.licence_ok(result(1, lic, '3.0')), lic)
        self.assertFalse(sounds.licence_ok(result(1, 'by', '')))                       # a licence without its version
        self.assertFalse(sounds.licence_ok(result(1, 'by', '3.0', url='https://creativecommons.org/licenses/by-nc/3.0/')))

    def test_cc0_first_then_cc_by_and_never_nc(self):
        asked = []

        def api(q, url):
            asked.append(q['license'])
            if q['license'] == 'cc0': return {'results': [result(1, 'cc0')]}
            return {'results': [result(2, 'by', '4.0'), result(3, 'by-nc', '3.0'), result(4, 'by', '3.0', title='gavel', dur=90000)]}
        self.web(api)
        c = sounds.search('gavel on wood', 'shot')
        self.assertEqual(asked, ['cc0', 'by'])                                # CC0 asked first; NC never asked for
        self.assertEqual([x['id'] for x in c], ['id-1', 'id-2'])              # NC dropped, a 90 s file is no one-shot
        self.assertEqual(c[1]['licence_name'], 'CC BY 4.0')

    def test_enough_cc0_means_cc_by_is_not_asked(self):
        asked = []
        self.web(lambda q, u: asked.append(q['license']) or {'results': [result(i) for i in range(4)]})
        sounds.search('gavel', 'shot')
        self.assertEqual(asked, ['cc0'])

    def test_a_bed_wants_a_longer_sound(self):
        self.web(lambda q, u: {'results': [result(1, dur=1500), result(2, dur=40000)]})
        self.assertEqual([c['id'] for c in sounds.search('gavel', 'bed')], ['id-2'])

    def test_the_source_page_has_the_last_word(self):
        c = sounds.candidate(result(1, 'by', '3.0'))
        self.web(page='<a href="https://creativecommons.org/licenses/by/4.0/">Attribution 4.0</a>')
        ok, how, page = sounds.verify(c)
        self.assertTrue(ok); self.assertEqual(page['licence_name'], 'CC BY 4.0'); self.assertIn('Openverse said CC BY 3.0', how)
        self.web(page='<a href="https://creativecommons.org/licenses/by-nc/4.0/">NonCommercial</a>')
        self.assertIs(sounds.verify(c)[0], False)
        self.web(page=sounds.Unavailable('freesound.org did not answer (HTTP 403)'))
        ok, how, _ = sounds.verify(c)
        self.assertIsNone(ok); self.assertIn('403', how)

    def test_a_page_with_another_licence_rejects_the_sound(self):
        self.web(lambda q, u: {'results': [result(1)]}, page='creativecommons.org/licenses/by-nd/4.0/')
        self.assertIsNone(sounds.fetch(sounds.candidate(result(1))))
        self.assertFalse(list((self.d / 'cache').glob('*.wav')))


class TestBusyOpenverse(Base):
    def test_a_504_is_retried_with_backoff(self):
        calls = []

        def urlopen(req, timeout):
            calls.append(timeout)
            if len(calls) < 3: raise urllib.error.HTTPError(req.full_url, 504, 'Gateway Timeout', {}, None)
            return io.BytesIO(b'{"results": []}')
        with mock.patch('urllib.request.urlopen', side_effect=urlopen):
            self.assertEqual(sounds._api({'q': 'x'}, timeout=7, retries=3), {'results': []})
        self.assertEqual(calls, [7, 7, 7])                                     # the short timeout every time

    def test_a_dead_openverse_is_a_message_and_remembered(self):
        def urlopen(req, timeout): raise urllib.error.HTTPError(req.full_url, 504, 'Gateway Timeout', {}, None)
        with mock.patch('urllib.request.urlopen', side_effect=urlopen) as m:
            r = sounds.find('gavel on wood', network=True, retries=1)
            self.assertIsNone(r['pick']); self.assertIn('not answering', r['why'])
            n = m.call_count
            r2 = sounds.find('gavel on wood', network=True, retries=1)        # not asked again for a while
            self.assertEqual(m.call_count, n); self.assertIn('not answering', r2['why'])

    def test_a_timeout_is_unavailable_not_a_crash(self):
        with mock.patch('urllib.request.urlopen', side_effect=TimeoutError('timed out')):
            with self.assertRaises(sounds.Unavailable) as e:
                sounds._api({'q': 'x'}, timeout=1, retries=2)
        self.assertIn('timed out', str(e.exception))


class TestCache(Base):
    def test_a_found_sound_is_cached_levelled_with_its_licence_record(self):
        seen = self.web(lambda q, u: {'results': [result(1, 'by', '3.0')]},
                        page='<a href="https://creativecommons.org/licenses/by/4.0/">by</a>')
        r = sounds.find('gavel on wood', network=True)
        rec = r['pick']
        self.assertEqual(rec['id'], 'id-1')
        f = Path(rec['file'])
        self.assertTrue(f.is_file() and f.parent == self.d / 'cache')
        lic = json.loads((self.d / 'cache/id-1.licence.json').read_text())
        for k in ('title', 'creator', 'licence', 'licence_version', 'source', 'page', 'attribution', 'credit', 'sha256', 'downloaded'):
            self.assertTrue(lic.get(k), k)
        self.assertEqual(lic['licence_name'], 'CC BY 4.0')                    # the page's licence, not Openverse's copy
        self.assertEqual(lic['openverse_licence'], 'CC BY 3.0')
        self.assertIn('CC BY 4.0', lic['attribution'])
        self.assertTrue(lic['verified'])
        with wave.open(str(f)) as w:                                          # the engine's format
            self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, 44100))
            self.assertLess(w.getnframes() / 44100, 1.6)                      # the 0.4 s of silence before it is gone
        self.assertAlmostEqual(mix.level(str(f), 'peak'), sounds.SHOT_PEAK, delta=0.5)
        n = len(seen)
        again = sounds.find('gavel on wood', network=True)                    # from the cache: no request at all
        self.assertEqual(len(seen), n); self.assertEqual(again['ranked_by'], 'cache'); self.assertEqual(again['pick']['id'], 'id-1')

    def test_cache_only_when_the_network_is_off(self):
        os.environ['VD_SOUNDS'] = '0'
        seen = self.web(lambda q, u: {'results': [result(1)]})
        r = sounds.find('gavel')
        self.assertIsNone(r['pick']); self.assertEqual(seen, [])

    def test_a_bed_is_levelled_by_its_running_level(self):
        x = sounds.prepare(np.random.default_rng(1).standard_normal(44100 * 40) * .05, 'bed')
        self.assertLessEqual(len(x), 44100 * sounds.BED_MAX)
        self.assertAlmostEqual(sounds.level(x, 'bed'), sounds.BED_ACTIVE, delta=0.6)
        self.assertLessEqual(np.abs(x).max(), 10 ** (sounds.CEILING / 20) + 1e-9)

    def test_silence_is_not_a_sound(self):
        with self.assertRaises(ValueError):
            sounds.prepare(np.zeros(44100), 'shot')

    def test_earshot_ranks_when_it_is_there(self):
        recs = [{'id': 'a', 'licence': 'cc0', 'file': str(self.d / 'a.wav')}, {'id': 'b', 'licence': 'by', 'file': str(self.d / 'b.wav')}]
        ears = {str((self.d / 'a.wav').resolve()): {'z': 1.0, 'verdict': 'weak', 'real': 'real or pro-produced'},
                str((self.d / 'b.wav').resolve()): {'z': 4.0, 'verdict': 'strong', 'real': 'real or pro-produced'}}
        with mock.patch.object(sounds, 'earshot', return_value=ears):
            out, how = sounds.rank('gavel', recs)
        self.assertEqual([r['id'] for r in out], ['b', 'a']); self.assertEqual(how, 'earshot')
        out, how = sounds.rank('gavel', recs)                                  # not installed: CC0 first, as searched
        self.assertEqual([r['id'] for r in out], ['a', 'b']); self.assertIn('not installed', how)


    def test_weak_cc0_matches_bring_in_cc_by(self):
        asked = []

        def api(q, url):
            asked.append(q['license'])
            return {'results': [result(i, 'cc0') for i in range(3)] if q['license'] == 'cc0' else [result(9, 'by', '4.0')]}
        self.web(api, page='creativecommons.org/publicdomain/zero/1.0/ creativecommons.org/licenses/by/4.0/')
        heard = []

        def ears(words, files):
            heard.append(words)
            return {str(Path(f).resolve()): ({'z': 4.2, 'verdict': 'strong'} if 'id-9' in f else {'z': 1.5, 'verdict': 'no match'}) for f in files}
        with mock.patch.object(sounds, 'earshot', side_effect=ears):
            r = sounds.find('gavel', network=True, listen='a wooden gavel striking a block')
        self.assertEqual(asked, ['cc0', 'by'])
        self.assertEqual(r['pick']['id'], 'id-9'); self.assertEqual(r['ranked_by'], 'earshot')
        self.assertEqual(set(heard), {'a wooden gavel striking a block'})
        lic = json.loads((self.d / 'cache/id-9.licence.json').read_text())
        self.assertEqual(lic['earshot']['a wooden gavel striking a block']['verdict'], 'strong')


class TestFilm(Base):
    def setUp(self):
        super().setUp()
        self.kit = self.d / 'kit'; self.kit.mkdir()
        for n in ('gavel', 'train_bed'):
            (self.kit / f'{n}.wav').write_bytes(wav_bytes())
        p = mock.patch.object(mix, 'SFX', self.kit); p.start(); self.addCleanup(p.stop)

    def cache(self, sid='id-1', lic='by', query='gavel on wood', kind='shot'):
        c = self.d / 'cache'; c.mkdir(exist_ok=True)
        sounds.write_wav(c / f"{sid}{'_bed' if kind == 'bed' else ''}.wav", sounds.prepare(sounds.decode(wav_bytes()), kind))
        r = sounds.candidate(result(sid.split('-')[-1], lic, '4.0' if lic == 'by' else '1.0'))
        (c / f'{sid}.licence.json').write_text(json.dumps({**r, 'credit': sounds.credit(r), 'verified': True}))
        if query: sounds._remember(sounds._qkey(query, kind), {'pick': sid, 'others': []})

    def test_offline_falls_back_to_the_procedural_kit(self):
        film = {'sounds': {'gavel': 'gavel on wood', 'train_bed': 'steam train', 'murmur': 'auction murmur', 'bell': {'query': 'bell', 'fallback': 'gavel'}},
                'lines': [{'id': 'l1', 'sfx': [{'name': 'gavel', 'at': 1}, {'name': 'murmur', 'at': 2}, {'name': 'bell', 'at': 3}], 'bed': 'train'}]}
        r = sounds.for_film(film, self.d / 'out/sfx')                         # the test guard blocks the network
        self.assertEqual(r['files'], {})
        self.assertEqual([c['name'] for c in film['lines'][0]['sfx']], ['gavel', 'gavel'])   # murmur left out, bell -> gavel
        self.assertEqual(film['lines'][0]['bed'], ['train'])
        self.assertTrue(any('murmur' in n and 'left out' in n for n in r['notes']))
        self.assertFalse(list((self.d / 'out/sfx').glob('*.wav')))

    def test_found_sounds_go_where_the_engine_looks_first(self):
        self.cache('id-1', 'by'); self.cache('id-2', 'cc0', query='steam train', kind='bed')
        film = {'sounds': {'gavel': 'gavel on wood', 'train_bed': 'steam train'},
                'lines': [{'id': 'l1', 'sfx': [{'name': 'gavel', 'at': 1}], 'bed': 'train'}]}
        r = sounds.for_film(film, self.d / 'out/sfx')
        self.assertEqual(set(r['files']), {'gavel', 'train_bed'})
        self.assertTrue((self.d / 'out/sfx/gavel.wav').is_file() and (self.d / 'out/sfx/train_bed.wav').is_file())
        self.assertEqual(mix.sound_file('gavel', False, self.d / 'out/sfx'), self.d / 'out/sfx/gavel.wav')
        self.assertEqual(mix.sound_file('train', True, self.d / 'out/sfx'), self.d / 'out/sfx/train_bed.wav')

    def test_a_pinned_found_id_and_its_fallback(self):
        self.cache('id-7', 'cc0', query=None)
        film = {'lines': [{'id': 'l1', 'sfx': [{'name': 'found:id-7', 'at': 1}, {'name': 'found:id-9', 'at': 2, 'fallback': 'gavel'},
                                                {'name': 'found:id-8', 'at': 3}]}]}
        r = sounds.for_film(film, self.d / 'out/sfx', network=False)
        self.assertEqual([c['name'] for c in film['lines'][0]['sfx']], ['found_id7', 'gavel'])   # id-8: no fallback, left out
        self.assertTrue((self.d / 'out/sfx/found_id7.wav').is_file())
        self.assertEqual(r['files']['found_id7']['id'], 'id-7')

    def test_a_render_drops_last_renders_found_files(self):
        self.cache('id-1', 'by')
        sounds.for_film({'sounds': {'gavel': 'gavel on wood'}, 'lines': []}, self.d / 'out/sfx')
        (self.d / 'out/sfx/mine.wav').write_bytes(b'x')                       # not ours: kept
        sounds.for_film({'lines': []}, self.d / 'out/sfx')
        self.assertFalse((self.d / 'out/sfx/gavel.wav').exists())
        self.assertTrue((self.d / 'out/sfx/mine.wav').exists())

    def test_every_found_sound_the_film_plays_is_credited(self):
        self.cache('id-1', 'by'); self.cache('id-2', 'cc0', query='steam train', kind='bed'); self.cache('id-3', 'by', query='clock')
        film = {'sounds': {'gavel': 'gavel on wood', 'train_bed': 'steam train', 'tick_slow': 'clock'}, 'lines': []}
        files = sounds.for_film(film, self.d / 'out/sfx')['files']
        scenes = [{'sfx': [{'name': 'gavel', 'at': 1}, {'name': 'gavel', 'at': 2}], 'beds': [{'name': 'train'}]}]   # tick_slow was dropped
        lines = sounds.credit_lines(sounds.used(scenes, files))
        self.assertEqual(lines[0], 'Sounds:')
        self.assertEqual(len(lines), 3)                                        # gavel once, the train bed; not the unplayed clock
        self.assertIn('by maker1, CC BY 4.0, via Freesound (https://freesound.org/people/maker1/sounds/1/)', lines[1])
        self.assertEqual(sounds.credit_lines([]), [])


class TestQuickFilmSounds(Base):
    """make() credits a found CC BY sound in credits.txt, the way credited photos are."""
    def test_quickfilm_credits_the_found_sound(self):
        from tests.test_quickfilm import FILM, HAVE_RENDER
        from director import quickfilm
        if not HAVE_RENDER: self.skipTest('node/ffmpeg not available')
        if not mix.sound_file('gavel'): self.skipTest('the procedural kit is not made (make-sfx.py)')
        TestFilm.cache(self, 'id-1', 'by')
        env = {k: os.environ.get(k) for k in ('VD_DRAFT_VOICE', 'VD_MUSIC_CACHE')}
        os.environ.update(VD_DRAFT_VOICE='offline-mock', VD_MUSIC_CACHE=str(self.d / 'music'))
        try:
            film = json.loads(json.dumps(FILM))
            film['sounds'] = {'gavel': 'gavel on wood', 'murmur': 'auction murmur'}
            film['lines'][0]['sfx'] = [{'name': 'gavel', 'at': 0.8}, {'name': 'murmur', 'at': 1.2}]
            f = self.d / 'film.yaml'; f.write_text(yaml.safe_dump(film, allow_unicode=True), encoding='utf-8')
            r = quickfilm.make(f, self.d / 'out', video=False)
        finally:
            for k, v in env.items():
                if v is None: os.environ.pop(k, None)
                else: os.environ[k] = v
        credits = (self.d / 'out/credits.txt').read_text()
        self.assertIn('Sounds:\n- “gavel on wood” by maker1, CC BY 4.0, via Freesound', credits)
        sb = json.loads((self.d / 'out/film.json').read_text())
        names = [c['name'] for c in sb['scenes'][0].get('sfx', [])]
        self.assertIn('gavel', names); self.assertNotIn('murmur', names)      # not found and not in the kit: left out, no crash
        self.assertTrue(any('murmur' in n for n in r['sounds']))


if __name__ == '__main__':
    unittest.main()
