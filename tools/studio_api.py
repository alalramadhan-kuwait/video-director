"""Claude's side of the studio web app (studio-app/): write a document, post a step, upload media, read the owner's taps.

The studio server is the `studio` Edge Function in the Time Keeper Supabase project (timekeeper-online/supabase/functions/
studio). Claude's key is a file outside the repository (VD_STUDIO_KEY_FILE, a JSON with "agent_token"); it is never printed.
  python3 tools/studio_api.py write film panerai patch.json ["what changed, for the owner"]
  python3 tools/studio_api.py step "أركّب الفلم…"            the now box and the log, in one call
  python3 tools/studio_api.py upload <local file> <path in studio-media>
  python3 tools/studio_api.py inbox                           the owner's taps since the last look (marks them read)
"""
from __future__ import annotations
import json, mimetypes, os, sys, time, urllib.parse, urllib.request
from pathlib import Path

URL = os.environ.get('VD_STUDIO_URL', 'https://ttshgrujnycapugrmyxs.supabase.co/functions/v1/studio')


def _key() -> str:
    f = os.environ.get('VD_STUDIO_KEY_FILE')
    if not f: raise SystemExit('set VD_STUDIO_KEY_FILE to the studio key file')
    return json.loads(Path(f).read_text())['agent_token']


def call(body: dict | None = None, *, method='POST', query='', data: bytes | None = None, ctype='application/json') -> dict:
    payload = data if data is not None else json.dumps(body or {}, ensure_ascii=False).encode()
    req = urllib.request.Request(URL + query, data=payload, method=method, headers={'Authorization': 'Bearer ' + _key(), 'Content-Type': ctype})
    for i in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read() or b'{}')
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == 2: raise SystemExit(f'studio: {e.code} {e.read()[:300]!r}')
            time.sleep(2 * (i + 1))


def write(collection: str, doc: str, patch: dict, note: str | None = None, kind='step') -> dict:
    return call({'action': 'write', 'collection': collection, 'id': doc, 'patch': patch, 'note': note, 'kind': kind})


def step(text: str, film='panerai', **now) -> dict:
    """What Claude is doing now, shown at the top of the app; also kept in the app's log."""
    at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    return write('film', film, {'now': {'busy': now.pop('busy', True), 'text': text, 'at': at, **now}}, note=text)


def upload(local: str, path: str) -> dict:
    ctype = mimetypes.guess_type(local)[0] or 'application/octet-stream'
    return call(method='PUT', query='?action=upload&path=' + urllib.parse.quote(path), data=Path(local).read_bytes(), ctype=ctype)


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a: raise SystemExit(__doc__)
    if a[0] == 'write': print(write(a[1], a[2], json.loads(Path(a[3]).read_text(encoding='utf-8')), a[4] if len(a) > 4 else None))
    elif a[0] == 'step': print(step(a[1]))
    elif a[0] == 'upload': print(upload(a[1], a[2]))
    elif a[0] == 'inbox': print(json.dumps(call({'action': 'inbox'}), ensure_ascii=False, indent=1))
    else: raise SystemExit(__doc__)
