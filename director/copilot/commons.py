"""Real photographs from Wikimedia Commons, before any drawing.

A file is used only when its own Commons page states a free licence (public domain, CC0, CC BY, CC BY-SA): that page is
the licence evidence, kept with the picture, and the author and licence are shown on screen. Non-commercial,
no-derivatives, fair-use and unknown licences are never used. A file must also match what the scene needs (every
distinctive word of the search in its file name; replicas never); when nothing matches, the scene keeps its drawing.
Free (no key, no cost). Off when VD_COMMONS=0 (the acceptance tests run on fixed material).
"""
from __future__ import annotations
import html, json, os, re, time, urllib.error, urllib.parse, urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'VideoDirector/0.1 (personal documentary tool; Wikimedia Commons API)'
FREE = re.compile(r'^(public domain|pd\b.*|cc0.*|cc by(-sa)? \d(\.\d)?.*|cc-by(-sa)?-\d.*)$', re.I)
NOT_FREE = re.compile(r'\b(nc|nd|non-?commercial|no ?deriv|fair use)\b', re.I)
FAKE = re.compile(r'\b(replica|fake|counterfeit|homage|clone|copy|knock-?off)\b', re.I)
STOP = {'photo', 'photograph', 'photographs', 'documented', 'scan', 'macro', 'image', 'picture', 'the', 'and', 'with', 'from',
        'early', 'front', 'page', 'real', 'genuine', 'close', 'shot', 'view', 'its', 'his', 'her', 'for', 'old', 'original'}


def enabled() -> bool:
    return os.environ.get('VD_COMMONS', '1') != '0'


def _text(v) -> str:
    t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', str(v or '')))).strip()
    m = re.fullmatch(r'(.+?)\s*\1', t)                     # Commons often repeats the author («Unknown author Unknown author»)
    return m.group(1) if m else t


def _get(params: dict, tries=3) -> dict:
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json'})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or i == tries - 1: raise
            time.sleep(min(30, int(e.headers.get('Retry-After') or 10)))      # Commons asks callers to slow down
    return {}


def words(query: str) -> list[str]:
    return [w for w in re.findall(r'[a-z0-9]+', query.lower()) if (len(w) >= 3 or w.isdigit()) and w not in STOP]


def licence_ok(name: str) -> bool:
    return bool(FREE.match(name.strip())) and not NOT_FREE.search(name)


def candidates(query: str, limit=10) -> list[dict]:
    """Files for `query` with a free licence stated on their page, best first. Each one carries its own evidence."""
    d = _get({'action': 'query', 'generator': 'search', 'gsrsearch': query, 'gsrnamespace': 6, 'gsrlimit': limit,
              'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime|size', 'iiurlwidth': 960})         # a standard thumbnail size: Commons refuses others (and big originals) to tools
    out = []
    for p in sorted((d.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 99)):
        ii = (p.get('imageinfo') or [{}])[0]
        m = ii.get('extmetadata') or {}
        lic = _text((m.get('LicenseShortName') or {}).get('value'))
        if ii.get('mime') not in ('image/jpeg', 'image/png') or min(ii.get('width', 0), ii.get('height', 0)) < 600 or not licence_ok(lic):
            continue
        out.append({'title': p['title'], 'page': ii.get('descriptionurl'), 'url': ii.get('thumburl') or ii.get('url'),
                    'width': ii.get('thumbwidth') or ii['width'], 'height': ii.get('thumbheight') or ii['height'], 'licence': lic,
                    'licence_url': _text((m.get('LicenseUrl') or {}).get('value')), 'author': _text((m.get('Artist') or {}).get('value'))[:80],
                    'name': _text((m.get('ObjectName') or {}).get('value'))[:200],
                    'about': ' '.join(_text((m.get(k) or {}).get('value')) for k in ('ObjectName', 'ImageDescription'))[:600]})
    return out


def best(query: str, cands: list[dict]) -> dict | None:
    """The first file whose name holds every distinctive word of the search; else none (the scene keeps its drawing)."""
    need = words(query)
    if not need: return None
    for c in cands:
        if FAKE.search(c['title'] + ' ' + c['about']): continue      # never a replica, homage or fake as a documentary picture
        hay = ' '.join(words(c['title'] + ' ' + c['name']))          # the file's own name, not a long description that mentions everything
        if all(re.search(r'\b' + re.escape(w) + r'\b', hay) for w in need):
            return c
    return None


def thumb(url: str, width=500) -> str | None:
    """The same file at a standard thumbnail width: Commons may refuse a near-original size to tools but serves these."""
    m = re.match(r'(https://upload\.wikimedia\.org/wikipedia/commons)/([0-9a-f])/([0-9a-f]{2})/([^?/]+)', url)
    return m and f'{m[1]}/thumb/{m[2]}/{m[3]}/{m[4]}/{width}px-{m[4]}'


def fetch(url: str) -> bytes:
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                return r.read(15 * 1024 * 1024)
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            if i == 2:
                alt = '/thumb/' not in url and thumb(url)                # an unscaled original refused: the standard 500 px one
                if not alt: raise
                return fetch(alt)
            time.sleep(min(30, int(e.headers.get('Retry-After') or 10)))
    return b''


def credit(c: dict) -> str:
    return f'{c["author"] or "Wikimedia Commons"} · {c["licence"]} · Wikimedia Commons'


def query_for(need: dict) -> str:
    """The search: the AI's own short query, else the distinctive words of what is needed ('documented photograph of
    Hans Wilsdorf' → 'hans wilsdorf'). Commons search finds little for a whole sentence."""
    return (need.get('query') or ' '.join(words(need.get('what') or ''))).strip()
