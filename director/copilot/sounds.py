"""Real recorded sounds from Openverse (free, no key, no account), with the procedural kit as the fallback.

Search  the Openverse audio API anonymously (https://api.openverse.org/v1/audio/): CC0 first, then CC BY; never NC,
        ND, SA or Sampling+. Freesound by default (Openverse's sound effects). One-shots are short (SHOT_S), beds longer
        (BED_S). Openverse is slow and often answers 504: each call has a short timeout and is retried with backoff,
        calls are spaced (20 a minute is the anonymous limit), and a failure is a message, never an exception.
Check   Openverse does not verify licences, so the record keeps the source's landing page (the evidence), and the
        page is re-checked when it can be read: a page that states another licence rejects the sound; a page that
        cannot be read (Freesound refuses some tools) leaves `verified: null`, said in the record and by the tool.
Cache   outside git (VD_SFX_CACHE, else ~/.cache/video-director/sfx): <id>.wav (one-shot) or <id>_bed.wav, the original
        download, and <id>.licence.json (title, creator, licence and version, source, page, attribution, credit, sha256,
        date). queries.json remembers each search's pick, and a failed or empty search for a while (no hammering).
Level   decoded to the engine's format (mono, 44.1 kHz, 16-bit WAV), silence trimmed, faded, and normalised to the
        levels the procedural kit sits at (mix.py then sets each sound's gain against the voice): a one-shot's
        loudest 50 ms at SHOT_PEAK dB, a bed's running level at BED_ACTIVE dB, never over -1 dBFS.
Rank    earshot (github.com/Leonxlnx/earshot, MIT, installed outside the repo; VD_EARSHOT=<its earshot command>)
        when it is there: how well each candidate matches the words, and whether it is a real recording. Without it:
        licence (CC0 first), the query's words in the title or tags, then Openverse's own order.
Film    `sounds:` in a film file maps a sound name to a search ({query, listen} or a pinned {id}); `name: found:<id>` on a
        line's sfx or bed uses one found sound directly. for_film() writes them to <out>/sfx/, where the engine looks
        first, and anything not found falls back to the procedural kit (vendor/paper-story/scripts/make-sfx.py): a
        render never fails because Openverse is down. Every found sound the film plays goes in credits.txt.
Off when VD_SOUNDS=0 (cache only, no network).
"""
from __future__ import annotations
import hashlib, json, math, os, re, shutil, socket, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request, wave
from pathlib import Path

import numpy as np

API = 'https://api.openverse.org/v1/audio/'
UA = 'VideoDirector/0.3 (personal documentary tool; Openverse API, anonymous)'
LICENCES = ('cc0', 'by')                       # in order of preference; nothing else is ever used
NAMES = {'cc0': 'CC0', 'by': 'CC BY'}
BAD = re.compile(r'(\bnc\b|\bnd\b|\bsa\b|-nc|-nd|-sa|sampling|non-?commercial|no-?deriv)', re.I)
SHOT_S, BED_S = (0.15, 12.0), (6.0, 240.0)     # seconds a candidate may last, one-shot / bed
SHOT_MAX, BED_MAX = 8.0, 30.0                  # seconds kept after trimming
SHOT_PEAK, BED_ACTIVE, CEILING = -12.0, -24.0, -1.0
SR = 44100
GAP = 3.2                                      # s between Openverse calls (anonymous: 20 a minute)
MISS_TTL = {'down': 6 * 3600, 'none': 7 * 86400}
STOP = {'sound', 'sounds', 'sfx', 'effect', 'effects', 'the', 'and', 'with', 'from', 'real', 'recording', 'one', 'shot',
        'bed', 'loop', 'ambience', 'ambient', 'background', 'old', 'for', 'on', 'of', 'in', 'a', 'an'}
_last = [0.0]


class Unavailable(RuntimeError):
    """Openverse (or the file's host) did not answer usefully. The message says why, in plain words."""


def enabled() -> bool:
    return os.environ.get('VD_SOUNDS', '1') != '0'


def cache_dir() -> Path:
    return Path(os.environ.get('VD_SFX_CACHE') or Path.home() / '.cache' / 'video-director' / 'sfx')


def words(text: str) -> list[str]:
    return [w for w in re.findall(r'[a-z0-9]+', str(text).lower()) if len(w) >= 3 and w not in STOP]


# ------------------------------------------------------------------------------------------------ network
def _http(url: str, *, timeout: float, retries: int, deadline: float | None = None, limit: int = 15 << 20,
          throttle: bool = False, retry_on=(403, 429, 500, 502, 503, 504)) -> bytes:
    """GET with a short timeout, retried with backoff on a busy answer (504, 429, a dropped connection). Raises
    Unavailable with a plain reason when it gives up."""
    why = ''
    for i in range(retries + 1):
        if deadline and time.monotonic() > deadline:
            why = why or 'out of time'; break
        if throttle:
            wait = _last[0] + GAP - time.monotonic()
            if wait > 0: time.sleep(wait)
            _last[0] = time.monotonic()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
                return r.read(limit)
        except urllib.error.HTTPError as e:
            why = f'HTTP {e.code}'
            if e.code not in retry_on: break
            ra = e.headers.get('Retry-After') if e.headers else None
            delay = float(ra) if ra and ra.isdigit() else 2.0 * 2 ** i
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError, OSError) as e:
            why = 'timed out' if 'timed out' in str(e) else (str(getattr(e, 'reason', e)) or type(e).__name__)[:80]
            delay = 2.0 * 2 ** i
        if i < retries:
            if deadline: delay = min(delay, max(0.0, deadline - time.monotonic()))
            time.sleep(min(delay, 30))
    raise Unavailable(f'{urllib.parse.urlsplit(url).netloc} did not answer ({why})')


def _api(params: dict | None = None, path: str = '', **kw) -> dict:
    url = API + path + ('?' + urllib.parse.urlencode(params) if params else '')
    data = _http(url, throttle=True, retry_on=(429, 500, 502, 503, 504), **kw)
    try:
        return json.loads(data)
    except ValueError:
        raise Unavailable('Openverse answered with something that is not JSON')


# ------------------------------------------------------------------------------------------------ licences
def licence_ok(r: dict) -> bool:
    """CC0 or CC BY only, with the licence named in full (code, version, deed); never NC, ND, SA or Sampling+."""
    lic = str(r.get('license') or '').lower()
    if lic not in LICENCES: return False
    url = str(r.get('license_url') or '')
    if BAD.search(url) or BAD.search(lic): return False
    return bool(r.get('license_version')) and ('creativecommons.org' in url)


def licence_name(r: dict) -> str:
    return f"{NAMES[r['license']]} {r['license_version']}".strip()


def _length_ok(r: dict, kind: str) -> bool:
    d = r.get('duration')
    if d is None: return kind == 'shot'          # unknown length: try it as a one-shot only; trimming caps it
    lo, hi = SHOT_S if kind == 'shot' else BED_S
    return lo <= d / 1000 <= hi


def candidate(r: dict, query: str = '') -> dict:
    """An Openverse result as this tool keeps it."""
    tags = [t.get('name', '') for t in r.get('tags') or [] if isinstance(t, dict)]
    return {'id': r['id'], 'title': str(r.get('title') or r['id'])[:200], 'creator': str(r.get('creator') or 'unknown')[:120],
            'creator_url': r.get('creator_url') or '', 'licence': r['license'], 'licence_version': str(r.get('license_version') or ''),
            'licence_name': licence_name(r), 'licence_url': r.get('license_url') or '', 'source': r.get('source') or r.get('provider') or '',
            'page': r.get('foreign_landing_url') or '', 'file_url': r.get('url') or '', 'filetype': r.get('filetype') or '',
            'duration': round((r.get('duration') or 0) / 1000, 2) or None, 'attribution': r.get('attribution') or '',
            'tags': tags[:20], 'openverse': r.get('detail_url') or f"{API}{r['id']}/", 'query': query}


def search(query: str, kind: str = 'shot', *, source: str = 'freesound', limit: int = 10, timeout: float = 20,
           retries: int = 3, deadline: float | None = None, licences: tuple = LICENCES) -> list[dict]:
    """Candidates for `query`, CC0 first then CC BY, of a length that suits a one-shot or a bed, best first. Raises
    Unavailable when Openverse does not answer at all."""
    out, seen, errors = [], set(), []
    for lic in licences:
        params = {'q': query, 'license': lic, 'page_size': 20, 'filter_dead': 'true', 'mature': 'false',
                  'length': 'shortest' if kind == 'shot' else 'shortest,short,medium'}
        if source: params['source'] = source
        try:
            d = _api(params, timeout=timeout, retries=retries, deadline=deadline)
        except Unavailable as e:
            errors.append(str(e)); continue
        for r in d.get('results') or []:
            if r.get('id') in seen or not licence_ok(r) or not _length_ok(r, kind): continue
            seen.add(r['id']); out.append(candidate(r, query))
        if len([c for c in out if c['licence'] == 'cc0']) >= 3: break          # enough CC0: no need to ask for CC BY
    if not out and len(errors) == len(licences):
        raise Unavailable(errors[0])
    need = words(query)
    hay = lambda c: set(words(c['title'] + ' ' + ' '.join(c['tags'])))
    out = [c for c in out if not need or hay(c) & set(need)]                   # at least one word of the search in its name or tags
    order = {c['id']: i for i, c in enumerate(out)}
    out.sort(key=lambda c: (LICENCES.index(c['licence']), -len(hay(c) & set(need)), order[c['id']]))
    return out[:limit]


def detail(sound_id: str, **kw) -> dict | None:
    """One Openverse sound by its id, if its licence is one we use."""
    r = _api(path=urllib.parse.quote(sound_id) + '/', **kw)
    return candidate(r) if r.get('id') and licence_ok(r) else None


DEED = re.compile(r'creativecommons\.org/(licenses|publicdomain)/([a-z+-]+)/(\d\.\d)', re.I)


def verify(c: dict, timeout: float = 15) -> tuple[bool | None, str, dict | None]:
    """Re-read the licence on the source's own page (the source is the authority, not Openverse's copy of it).
    True: the page links a CC0 or CC BY deed; when it names another version (Freesound moved many sounds from
    CC BY 3.0 to 4.0) the page's licence is returned and kept. False: it states only another licence (NC, ND, SA,
    Sampling+). None: the page could not be read or names no deed (the record says so)."""
    if not c.get('page'): return None, 'no source page', None
    try:
        html = _http(c['page'], timeout=timeout, retries=1, limit=3 << 20, retry_on=(429, 500, 502, 503, 504)).decode('utf-8', 'replace')
    except Unavailable as e:
        return None, f'source page not readable: {e}', None
    deeds = {(m.group(2).lower().replace('zero', 'cc0'), m.group(3)) for m in DEED.finditer(html)}
    good = [d for d in deeds if d[0] in LICENCES]
    if good:
        lic, ver = next((d for d in good if d == (c['licence'], c['licence_version'])), sorted(good, key=lambda d: LICENCES.index(d[0]))[0])
        page = {'licence': lic, 'licence_version': ver, 'licence_name': f'{NAMES[lic]} {ver}',
                'licence_url': f"https://creativecommons.org/{'publicdomain/zero' if lic == 'cc0' else 'licenses/by'}/{ver}/"}
        same = (lic, ver) == (c['licence'], c['licence_version'])
        return True, f"source page states {page['licence_name']}" + ('' if same else f" (Openverse said {c['licence_name']})"), page
    if deeds:
        return False, f"source page states another licence ({'-'.join(sorted(deeds)[0])})", None
    return None, 'source page names no licence deed', None


# ------------------------------------------------------------------------------------------------ audio
def _read_wav(data: bytes) -> np.ndarray:
    with wave.open(_io(data)) as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw != 2 or sr != SR: raise ValueError('needs ffmpeg')
    x = np.frombuffer(raw, '<i2').astype(np.float64) / 32768
    return x.reshape(-1, ch).mean(axis=1) if ch > 1 else x


def _io(data: bytes):
    import io
    return io.BytesIO(data)


def decode(data: bytes) -> np.ndarray:
    """Any audio file as mono 44.1 kHz floats (16-bit 44.1 kHz WAV directly; anything else through ffmpeg)."""
    if data[:4] == b'RIFF':
        try:
            return _read_wav(data)
        except (ValueError, wave.Error, EOFError):
            pass
    ff = shutil.which('ffmpeg')
    if not ff: raise RuntimeError('ffmpeg is needed to decode a downloaded sound')
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / 'in'; src.write_bytes(data)
        r = subprocess.run([ff, '-v', 'error', '-i', str(src), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-'],
                           capture_output=True, timeout=120)
    if r.returncode or not r.stdout: raise RuntimeError('ffmpeg could not read the download: ' + r.stderr.decode()[-200:])
    return np.frombuffer(r.stdout, '<i2').astype(np.float64) / 32768


def _frames_db(x: np.ndarray, n: int) -> np.ndarray:
    m = len(x) // n
    if m == 0: return np.array([10 * math.log10(max(float((x ** 2).mean()) if len(x) else 0, 1e-12))])
    return 10 * np.log10(np.maximum((x[:m * n].reshape(m, n) ** 2).mean(axis=1), 1e-12))


def trim(x: np.ndarray, below: float = 45, floor: float = -65) -> np.ndarray:
    """The sound without its silence at either end: 10 ms frames more than `below` dB under the loudest (or under
    `floor` dBFS) are cut, keeping 10 ms before the first and 30 ms after the last."""
    n = SR // 100
    db = _frames_db(x, n)
    keep = np.where(db > max(floor, db.max() - below))[0]
    if not len(keep): return x[:0]
    a, b = max(0, (keep[0] - 1) * n), min(len(x), (keep[-1] + 4) * n)
    return x[a:b]


def level(x: np.ndarray, kind: str) -> float:
    """dB as mix.level measures it: a one-shot's loudest 50 ms, a bed's mean over its frames within 30 dB of the top."""
    db = _frames_db(x, 2205)
    if kind == 'shot': return float(db.max())
    p = 10 ** (db / 10)
    return float(10 * math.log10(p[p >= p.max() * 1e-3].mean()))


def prepare(x: np.ndarray, kind: str) -> np.ndarray:
    """Trimmed, capped (a faded tail when cut), faded at both ends, normalised to the kit's level, under the ceiling."""
    x = trim(np.asarray(x, dtype=np.float64))
    if len(x) < SR // 50: raise ValueError('the sound is silent or too short')
    cap = int(SR * (SHOT_MAX if kind == 'shot' else BED_MAX))
    cut = len(x) > cap
    x = x[:cap].copy()
    fi = int(SR * (0.003 if kind == 'shot' else 0.4))
    fo = int(SR * ((0.5 if cut else 0.03) if kind == 'shot' else 0.6))
    x[:fi] *= np.linspace(0, 1, fi)
    x[-fo:] *= np.linspace(1, 0, fo)
    x = x * 10 ** (((SHOT_PEAK if kind == 'shot' else BED_ACTIVE) - level(x, kind)) / 20)
    peak = float(np.abs(x).max())
    lim = 10 ** (CEILING / 20)
    return x * (lim / peak) if peak > lim else x


def write_wav(path: Path, x: np.ndarray) -> None:
    tmp = path.with_suffix('.tmp')
    with wave.open(str(tmp), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    tmp.replace(path)


AUDIO_MAGIC = (b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2', b'OggS', b'RIFF', b'fLaC')


def _wav_path(sid: str, kind: str) -> Path:
    return cache_dir() / f"{sid}{'_bed' if kind == 'bed' else ''}.wav"


def _rec_path(sid: str) -> Path:
    return cache_dir() / f'{sid}.licence.json'


def cached(sid: str, kind: str = 'shot') -> dict | None:
    """The cached sound and its licence record, if both are there."""
    w, r = _wav_path(sid, kind), _rec_path(sid)
    if not (w.is_file() and r.is_file()): return None
    try:
        return {**json.loads(r.read_text(encoding='utf-8')), 'file': str(w), 'kind': kind}
    except ValueError:
        return None


def fetch(c: dict, kind: str = 'shot', *, timeout: float = 20, retries: int = 3, check: bool = True,
          deadline: float | None = None) -> dict | None:
    """One candidate downloaded, licence re-checked on its page, made into the engine's WAV and cached with its record.
    None when the download fails, is not audio, or the page states another licence."""
    have = cached(c['id'], kind)
    if have: return have
    d = cache_dir(); d.mkdir(parents=True, exist_ok=True)
    rec = json.loads(_rec_path(c['id']).read_text(encoding='utf-8')) if _rec_path(c['id']).is_file() else None
    orig = next(iter(sorted(d.glob(f"{c['id']}.orig.*"))), None)
    if rec and orig and orig.is_file():
        data = orig.read_bytes()                                       # made before as the other kind: no new download
    else:
        if not c.get('file_url'): return None
        try:
            data = _http(c['file_url'], timeout=timeout, retries=retries, deadline=deadline)
        except Unavailable:
            return None
        if len(data) < 1000 or not data.startswith(AUDIO_MAGIC): return None
        ok, how, page = verify(c) if check else (None, 'not checked', None)
        if ok is False: return None
        if page and page['licence_name'] != c['licence_name']:          # the page's own licence wins over Openverse's copy
            c = {**c, **page, 'openverse_licence': c['licence_name'],
                 'attribution': f"“{c['title']}” by {c['creator']} is licensed under {page['licence_name']}. "
                                f"To view a copy of this license, visit {page['licence_url']}."}
        ext = re.sub(r'[^a-z0-9]', '', (c.get('filetype') or 'bin').lower())[:5] or 'bin'
        orig = d / f"{c['id']}.orig.{ext}"; orig.write_bytes(data)
        rec = {k: c.get(k) for k in ('id', 'title', 'creator', 'creator_url', 'licence', 'licence_version', 'licence_name',
                                     'licence_url', 'source', 'page', 'file_url', 'attribution', 'openverse', 'openverse_licence', 'query')}
        rec.update(credit=credit(c), verified=ok, verified_how=how, commercial_use=True,
                   downloaded=time.strftime('%Y-%m-%d'), sha256=hashlib.sha256(data).hexdigest(), found_via='Openverse')
    try:
        x = prepare(decode(data), kind)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        return None
    write_wav(_wav_path(c['id'], kind), x)
    rec[f'seconds_{kind}'] = round(len(x) / SR, 2)
    _rec_path(c['id']).write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
    return cached(c['id'], kind)


def credit(c: dict) -> str:
    """The credit line for the film's credits (the post caption): title, creator, licence, source."""
    src = {'freesound': 'Freesound', 'wikimedia_audio': 'Wikimedia Commons', 'jamendo': 'Jamendo'}.get(c.get('source'), c.get('source') or '')
    return f"“{c['title']}” by {c['creator']}, {c['licence_name']}" + (f', via {src}' if src else '')


# ------------------------------------------------------------------------------------------------ earshot
def earshot_bin() -> str | None:
    b = os.environ.get('VD_EARSHOT') or shutil.which('earshot')
    return b if b and Path(b).exists() else None


def earshot(query: str, files: list[str], timeout: float = 600) -> dict[str, dict] | None:
    """earshot's opinion of each file: match to the words (z, verdict) and whether it is a real recording (p_real).
    None when earshot is not installed or fails (the ranking then uses licence and words)."""
    b = earshot_bin()
    if not b or not files: return None
    env = {**os.environ, 'EARSHOT_THREADS': os.environ.get('EARSHOT_THREADS', str(max(1, (os.cpu_count() or 2) - 1)))}
    out: dict[str, dict] = {str(Path(f).resolve()): {} for f in files}
    try:
        r = subprocess.run([b, 'rank', query, *files, '--json'], capture_output=True, text=True, timeout=timeout, env=env)
        for x in json.loads(r.stdout).get('results', []):
            out.setdefault(str(Path(x['path']).resolve()), {}).update(z=x.get('z'), verdict=x.get('verdict'), like=x.get('sounds_most_like'))
        r = subprocess.run([b, 'realness', *files, '--json'], capture_output=True, text=True, timeout=timeout, env=env)
        for x in json.loads(r.stdout).get('files', []):
            out.setdefault(str(Path(x['path']).resolve()), {}).update(p_real=x.get('p_real'), real=x.get('verdict'))
    except (OSError, ValueError, subprocess.TimeoutExpired, KeyError, TypeError):
        return None
    return out


VERDICT = {'strong': 0, 'plausible': 1, 'weak': 2, 'no match': 3}


def rank(query: str, recs: list[dict], use_earshot: bool = True) -> tuple[list[dict], str]:
    """Downloaded candidates, best first: earshot's match verdict (a likely code-made sound last), then CC0 before
    CC BY, then earshot's score; without earshot, the search's own order (CC0 first, words in the name)."""
    ears = earshot(query, [r['file'] for r in recs]) if use_earshot and len(recs) > 1 else None
    if not ears: return recs, 'licence and words (earshot not installed)' if use_earshot and len(recs) > 1 and not earshot_bin() else 'licence and words'
    for r in recs:
        r['earshot'] = {k: v for k, v in ears.get(str(Path(r['file']).resolve()), {}).items() if v is not None}
    def key(r):
        e = r.get('earshot', {})
        synth = e.get('real') == 'likely code-synthesized'
        return (VERDICT.get(e.get('verdict'), 2) + (2 if synth else 0), LICENCES.index(r['licence']), -(e.get('z') or 0))
    return sorted(recs, key=key), 'earshot'


# ------------------------------------------------------------------------------------------------ find
def _qkey(query: str, kind: str) -> str:
    return f"{kind}:{' '.join(query.lower().split())}"


def _index() -> dict:
    f = cache_dir() / 'queries.json'
    try:
        return json.loads(f.read_text(encoding='utf-8')) if f.is_file() else {}
    except ValueError:
        return {}


def _remember(key: str, entry: dict) -> None:
    d = cache_dir(); d.mkdir(parents=True, exist_ok=True)
    ix = _index(); ix[key] = {**entry, 'when': time.time()}
    (d / 'queries.json').write_text(json.dumps(ix, ensure_ascii=False, indent=1), encoding='utf-8')


def find(query: str, kind: str = 'shot', *, network: bool | None = None, take: int = 4, use_earshot: bool = True,
         timeout: float = 20, retries: int = 3, deadline: float | None = None, fresh: bool = False,
         listen: str | None = None) -> dict:
    """The best real sound for `query`: {'pick': record or None, 'others': [records], 'why': reason when none,
    'ranked_by': how}. The cache answers first; a search that failed or found nothing lately is not repeated.
    `listen`: the words earshot judges the candidates against (default the query; a fuller description helps:
    "a wooden gavel striking a block"). When earshot hears no good CC0 match, CC BY candidates are fetched too."""
    network = enabled() if network is None else network
    key = _qkey(query, kind)
    seen = _index().get(key) or {}
    if not fresh and seen.get('pick') and (rec := cached(seen['pick'], kind)):
        return {'pick': rec, 'others': [r for i in seen.get('others', []) if (r := cached(i, kind))], 'why': None, 'ranked_by': 'cache'}
    if not fresh and seen.get('miss') and time.time() - seen.get('when', 0) < MISS_TTL.get(seen['miss'], 0):
        return {'pick': None, 'others': [], 'why': seen.get('why', 'nothing found earlier'), 'ranked_by': 'cache'}
    if not network:
        return {'pick': None, 'others': [], 'why': 'not in the cache and the network is off (VD_SOUNDS=0)', 'ranked_by': None}
    try:
        cands = search(query, kind, timeout=timeout, retries=retries, deadline=deadline)
    except Unavailable as e:
        why = f'Openverse is not answering right now ({e}); the procedural sound is used'
        _remember(key, {'miss': 'down', 'why': why})
        return {'pick': None, 'others': [], 'why': why, 'ranked_by': None, 'candidates': []}
    recs = []
    for c in cands:
        if len(recs) >= take: break
        r = fetch(c, kind, timeout=timeout, retries=retries, deadline=deadline)
        if r: recs.append(r)
    if not recs:
        why = ('no CC0 or CC BY sound of the right length matches' if not cands else
               'the matching sounds could not be downloaded or their page states another licence')
        _remember(key, {'miss': 'none' if not cands else 'down', 'why': why})
        return {'pick': None, 'others': [], 'why': why, 'ranked_by': None, 'candidates': cands}
    recs, how = rank(listen or query, recs, use_earshot)
    weak = how == 'earshot' and recs[0].get('earshot', {}).get('verdict') in ('weak', 'no match')
    if weak and not any(c['licence'] == 'by' for c in cands):          # only weak CC0 matches: hear the CC BY ones too
        try:
            more = search(query, kind, timeout=timeout, retries=retries, deadline=deadline, licences=('by',))
        except Unavailable:
            more = []
        for c in more[:take]:
            r = fetch(c, kind, timeout=timeout, retries=retries, deadline=deadline)
            if r: recs.append(r)
        cands = cands + more
        recs, how = rank(listen or query, recs, use_earshot)
    for r in recs:                                                     # earshot's opinion goes in the licence record too
        if r.get('earshot'):
            p = _rec_path(r['id']); d = json.loads(p.read_text(encoding='utf-8')); d.setdefault('earshot', {})[listen or query] = r['earshot']
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    _remember(key, {'pick': recs[0]['id'], 'others': [r['id'] for r in recs[1:]], 'ranked_by': how})
    return {'pick': recs[0], 'others': recs[1:], 'why': None, 'ranked_by': how, 'candidates': cands}


def by_id(sound_id: str, kind: str = 'shot', *, network: bool | None = None, **kw) -> dict | None:
    """A pinned Openverse sound: from the cache, else looked up and fetched (None when it cannot be)."""
    have = cached(sound_id, kind)
    if have: return have
    if not (enabled() if network is None else network): return None
    try:
        c = detail(sound_id, timeout=kw.get('timeout', 20), retries=kw.get('retries', 3), deadline=kw.get('deadline'))
    except Unavailable:
        return None
    return c and fetch(c, kind, **kw)


# ------------------------------------------------------------------------------------------------ the film
FOUND = 'found:'


def _proc(name: str, bed: bool) -> bool:
    from ..studio import mix
    return mix.sound_file(name, bed) is not None


def for_film(film: dict, sfx_dir: Path, *, network: bool | None = None, budget: float = 150) -> dict:
    """The film's found sounds in sfx_dir (where the engine looks before its own kit). Changes the film's cues in place
    where a sound has to fall back or be left out. Returns {'files': {stem: record}, 'notes': [plain words]}.
    Never raises: anything that goes wrong leaves the procedural sound."""
    sfx_dir = Path(sfx_dir); sfx_dir.mkdir(parents=True, exist_ok=True)
    manifest = sfx_dir / 'found.json'
    try:
        old = json.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() else {}
    except ValueError:
        old = {}
    for stem in old:                                                   # last render's found files: only those we wrote
        f = sfx_dir / f'{stem}.wav'
        if re.fullmatch(r'[A-Za-z0-9_.-]+', stem) and f.is_file(): f.unlink()
    deadline = time.monotonic() + budget
    files, notes, rename = {}, [], {}

    def place(rec: dict, stem: str) -> None:
        shutil.copyfile(rec['file'], sfx_dir / f'{stem}.wav'); files[stem] = rec

    def safe(fn, *a, **k):
        try:
            return fn(*a, **k)
        except Exception as e:                                         # noqa: BLE001  a render never fails on a sound
            return {'pick': None, 'why': f'{type(e).__name__}: {str(e)[:100]}'} if fn is find else None

    for key, spec in (film.get('sounds') or {}).items():
        spec = {'query': spec} if isinstance(spec, str) else dict(spec or {})
        bed = str(key).endswith('_bed') or bool(spec.get('bed'))
        base = str(key)[:-4] if str(key).endswith('_bed') else str(key)
        kind = 'bed' if bed else 'shot'
        stem = base + ('_bed' if bed else '')
        if spec.get('id'):
            rec = safe(by_id, str(spec['id']), kind, network=network, deadline=deadline, retries=2)
            why = None if rec else f"sound {spec['id']} is not cached and could not be fetched"
        elif spec.get('query'):
            r = safe(find, str(spec['query']), kind, network=network, deadline=deadline, retries=2, listen=spec.get('listen'))
            rec, why = r.get('pick'), r.get('why')
        else:
            rec, why = None, 'no query: or id: given'
        if rec:
            place(rec, stem); notes.append(f"{stem}: {rec['title']} by {rec['creator']} ({rec['licence_name']})" +
                                           ('' if rec.get('verified') else ', licence not re-checked on its page'))
        elif _proc(base, bed):
            notes.append(f'{stem}: the procedural sound ({why})')
        else:
            fb = spec.get('fallback')
            rename[base] = fb if fb and _proc(fb, bed) else None
            notes.append(f'{stem}: ' + (f'the procedural {fb!r} ({why})' if rename[base] else f'left out: nothing found and no fallback ({why})'))

    def resolve(name: str, cue: dict, bed: bool):
        """The name the engine will find for a cue: a found file, the procedural kit, the cue's fallback, or None (drop)."""
        if isinstance(name, str) and name.startswith(FOUND):
            sid = name[len(FOUND):].strip()
            stem = 'found_' + re.sub(r'[^A-Za-z0-9]', '', sid)[:12] + ('_bed' if bed else '')
            if stem in files: return stem.removesuffix('_bed')
            rec = safe(by_id, sid, 'bed' if bed else 'shot', network=network, deadline=deadline, retries=2)
            if rec:
                place(rec, stem); notes.append(f"{name}: {rec['title']} by {rec['creator']} ({rec['licence_name']})")
                return stem.removesuffix('_bed')
            fb = cue.get('fallback')
            notes.append(f'{name}: ' + (f'not available, the procedural {fb!r}' if fb else 'not available and no fallback: left out'))
            return fb if fb and _proc(fb, bed) else None
        if name in rename:
            return rename[name]
        return name

    for ln in film.get('lines') or []:
        if ln.get('sfx'):
            keep = []
            for c in ln['sfx']:
                c = {'name': c} if isinstance(c, str) else dict(c)
                n = resolve(c.get('name'), c, False)
                if n: keep.append({**c, 'name': n})
            ln['sfx'] = keep
        if 'bed' in ln and ln['bed'] not in (None, 'none', False):
            beds = ln['bed'] if isinstance(ln['bed'], list) else [ln['bed']]
            keep = []
            for b in beds:
                b = {'name': b} if isinstance(b, str) else dict(b)
                n = resolve(b.get('name'), b, True)
                if n: keep.append({**b, 'name': n} if len(b) > 1 else n)
            ln['bed'] = keep or 'none'
    manifest.write_text(json.dumps({k: v['id'] for k, v in files.items()}, indent=1), encoding='utf-8')
    return {'files': files, 'notes': notes}


def used(scenes: list[dict], files: dict[str, dict]) -> list[dict]:
    """The found sounds a film really plays (after the mix dropped what it had to), each once, in order of use."""
    out, seen = [], set()
    for sc in scenes:
        names = [(c.get('name'), False) for c in sc.get('sfx') or []] + [(b.get('name'), True) for b in sc.get('beds') or []]
        for n, bed in names:
            rec = (files.get(f'{n}_bed') if bed else None) or files.get(n)
            if rec and rec['id'] not in seen:
                seen.add(rec['id']); out.append(rec)
    return out


def credit_lines(recs: list[dict]) -> list[str]:
    """credits.txt lines: every CC BY sound must be credited; CC0 ones are listed too (the evidence trail)."""
    if not recs: return []
    return ['Sounds:'] + [f"- {r['credit']} ({r['page']})" for r in recs]
