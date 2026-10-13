"""Wiring for the dashboard: where its files live, how a snapshot is made, and the static (Artifact) build.

    python -m director.dashboard.build OUT_DIR      # static copy with an embedded snapshot, for review on a phone
"""
from __future__ import annotations
import json, os, shutil, sys
from pathlib import Path

from ..events import EventLog
from . import history, media
from .snapshot import build as _build

ROOT = Path(__file__).resolve().parents[2]
VAR = Path(os.environ.get('VD_DASHBOARD_VAR') or ROOT / 'var/dashboard')   # tests point this at a copy
MEDIA = VAR / 'media'
TEMPLATE = Path(__file__).parent / 'app.html'


def _scratch():
    from tests.fixtures import S, RO_AUDIO
    return S, RO_AUDIO


def log() -> EventLog:
    return EventLog(VAR / 'events.sqlite')


def prepare():
    """Import reconstructed history (idempotent) and make the media once (tracked tasks)."""
    S, ro_audio = _scratch()
    L = log()
    history.import_ep7(L, S); history.import_royal_oak(L, S)
    if not (MEDIA / 'ep7/clips').exists():
        media.ep7_media(L, S, ROOT / 'var/review/ep7-final', MEDIA)
    if not (MEDIA / 'royal-oak/audio').exists():
        media.royal_oak_media(L, ro_audio, MEDIA)
    return L


def snapshot(extra_decisions=None) -> dict:
    S, _ = _scratch()
    vd = json.loads((ROOT / 'var/pages/voice-royal-oak/data.json').read_text(encoding='utf-8'))
    dd = json.loads((ROOT / 'var/pages/directions/data.json').read_text(encoding='utf-8'))
    return _build(log(), S, vd, dd, extra_decisions)


def locate(item: str):
    """project, video, scene for a review item id (used to file the decision event)."""
    if item.startswith('voice-dh-'): return 'diabetes-history', 'ep6', None
    if item.startswith('voice-'): return 'timekeeper', 'royal-oak', item.split('-')[1] + '-' + item.split('-')[2]
    if item.startswith('art-ep7-'): return 'diabetes-history', 'ep7', item.split('-', 2)[2]
    if item.startswith('ep7-'): return 'diabetes-history', 'ep7', item.split('-')[1]          # gallery version ep7-<scene>-<v>
    if item.startswith('f_'): return 'diabetes-history', 'ep7', None
    if item == 'final-ep7': return 'diabetes-history', 'ep7', None
    if item == 'direction-timekeeper' or item == 'eng-paper-banner': return 'timekeeper', None, None
    if item == 'direction-diabetes': return 'diabetes-history', None, None
    raise ValueError(f'unknown review item {item!r}')


def render_app(snap: dict, mode: str) -> str:
    html = TEMPLATE.read_text(encoding='utf-8')
    return html.replace('__MODE__', mode).replace('__DATA__', json.dumps(snap, ensure_ascii=False).replace('</', '<\\/'))


def build_static(out_dir) -> list[str]:
    """A self-contained copy (page + media) for an Artifact; decisions there go to the page's store."""
    prepare()
    out = Path(out_dir)
    if (out / 'media').exists():
        shutil.rmtree(out / 'media')
    shutil.copytree(MEDIA, out / 'media')
    (out / 'index.html').write_text(render_app(snapshot(), mode='artifact'), encoding='utf-8')
    return sorted(str(p.relative_to(out)) for p in (out / 'media').rglob('*') if p.is_file())


if __name__ == '__main__':
    files = build_static(sys.argv[1])
    print(len(files), 'media files')
