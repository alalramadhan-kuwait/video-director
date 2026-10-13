"""Immutable take store.

* A take's KEY is the sha256 of exactly what a provider is asked to do (provider, voice, model, settings, seed,
  output format, provider input text). Same key = same request = never billed twice.
* The library version and the approved script line are recorded on the take but are NOT part of the key:
  a dictionary edit that does not change what is sent must not make unchanged lines look new.
* Audio is stored once, addressed by its own sha256, and made read-only. Take records are write-once JSON.
* Status (candidate / approved / rejected) is never written into the take record; it is derived from an
  append-only event log, so approving or rejecting cannot modify or overwrite anything.
"""
from __future__ import annotations
import hashlib, json, os, stat, time
from pathlib import Path

KEY_FIELDS = ('provider', 'voice_id', 'model', 'settings', 'seed', 'output_format', 'provider_input')
STATUS_FLOW = {None: {'candidate', 'approved', 'rejected'}, 'candidate': {'approved', 'rejected'},
               'rejected': set(), 'approved': set()}          # approved and rejected are final for that take


class TakeStoreError(Exception):
    pass


def canonical(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def take_key(request: dict) -> str:
    missing = [f for f in KEY_FIELDS if f not in request]
    if missing:
        raise TakeStoreError(f'request missing {missing}')
    return 't_' + hashlib.sha256(canonical({f: request[f] for f in KEY_FIELDS})).hexdigest()


class TakeStore:
    def __init__(self, root):
        self.root = Path(root)
        for d in ('objects', 'takes', 'events'):
            (self.root / d).mkdir(parents=True, exist_ok=True)
        self.log = self.root / 'events' / 'status.jsonl'

    # ------------------------------------------------------------------ audio objects
    def _put_object(self, data: bytes, ext: str) -> tuple[str, Path]:
        h = hashlib.sha256(data).hexdigest()
        p = self.root / 'objects' / h[:2] / f'{h}.{ext}'
        if p.exists():
            if hashlib.sha256(p.read_bytes()).hexdigest() != h:
                raise TakeStoreError(f'object {p} is corrupted')
            return h, p
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix('.tmp')
        tmp.write_bytes(data)
        os.replace(tmp, p)
        os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        return h, p

    # ------------------------------------------------------------------ takes
    def put(self, request: dict, audio: bytes, ext='mp3', meta: dict | None = None, status='candidate', by='system'):
        """Store a take. Returns its key. Re-putting the same request with the same audio is a no-op;
        with different audio it is refused (a take is never overwritten)."""
        key = take_key(request)
        audio_sha, path = self._put_object(audio, ext)
        rec_path = self.root / 'takes' / f'{key}.json'
        if rec_path.exists():
            old = json.loads(rec_path.read_text(encoding='utf-8'))
            if old['audio']['sha256'] != audio_sha:
                raise TakeStoreError(f'{key} already exists with different audio; takes are never overwritten')
            return key
        rec = {'take': key, 'request': {f: request[f] for f in KEY_FIELDS},
               'audio': {'sha256': audio_sha, 'path': str(path.relative_to(self.root)), 'bytes': len(audio), 'ext': ext},
               'meta': meta or {}, 'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        tmp = rec_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(tmp, rec_path)
        os.chmod(rec_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.set_status(key, status, by=by, reason='created')
        return key

    def get(self, key: str) -> dict | None:
        p = self.root / 'takes' / f'{key}.json'
        return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None

    def audio_path(self, key: str) -> Path:
        return self.root / self.get(key)['audio']['path']

    def verify(self, key: str) -> bool:
        rec = self.get(key)
        return rec is not None and hashlib.sha256(self.audio_path(key).read_bytes()).hexdigest() == rec['audio']['sha256']

    # ------------------------------------------------------------------ status (append-only events)
    def events(self, key: str | None = None):
        if not self.log.exists():
            return []
        rows = [json.loads(l) for l in self.log.read_text(encoding='utf-8').splitlines() if l.strip()]
        return [r for r in rows if key is None or r['take'] == key]

    def status(self, key: str):
        ev = self.events(key)
        return ev[-1]['status'] if ev else None

    def set_status(self, key: str, status: str, by: str, reason: str = ''):
        if self.get(key) is None:
            raise TakeStoreError(f'unknown take {key}')
        cur = self.status(key)
        if status not in STATUS_FLOW[cur]:
            raise TakeStoreError(f'{key}: cannot go from {cur} to {status}')
        with open(self.log, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'take': key, 'status': status, 'by': by, 'reason': reason,
                                'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, ensure_ascii=False) + '\n')

    def all(self):
        return [p.stem for p in sorted((self.root / 'takes').glob('t_*.json'))]
