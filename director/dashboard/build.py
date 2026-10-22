"""Wiring for the dashboard: where its files live, how a snapshot is made, and the static (Artifact) build.

    python -m director.dashboard.build OUT_DIR      # static copy with an embedded snapshot, for review on a phone
"""
from __future__ import annotations
import json, os, shutil, sys
from pathlib import Path

from ..events import EventLog
from . import history, media, samples
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


def has_archive() -> bool:
    return (ROOT / 'var/review/ep7-final/pack.json').exists() and (ROOT / 'var/pages').exists()


def ensure_sounds():
    """The paper sounds the scenes are mixed with are made locally (deterministic, free) the first time; a new computer has none."""
    import subprocess
    from ..studio.engine import ENGINE
    if not all((ENGINE / 'assets/sfx' / f).exists() for f in ('paper_slide.wav', 'underwater.wav')):    # the kit grew: remake if one is missing
        subprocess.run([sys.executable, str(ENGINE / 'scripts/make-sfx.py')], check=True, capture_output=True, timeout=300)


def prepare():
    """Import reconstructed history (idempotent) and make the media once (tracked tasks)."""
    ensure_sounds()
    L = log()
    if not has_archive():                                            # a new computer has no archive: the Studio works without it
        return L
    S, ro_audio = _scratch()
    history.import_ep7(L, S); history.import_royal_oak(L, S)
    if not (MEDIA / 'ep7/clips').exists():
        media.ep7_media(L, S, ROOT / 'var/review/ep7-final', MEDIA)
    if not (MEDIA / 'royal-oak/audio').exists():
        media.royal_oak_media(L, ro_audio, MEDIA)
    if not (MEDIA / 'timekeeper/endcard/endcard.mp4').exists():
        samples.tk_endcard(L, S, MEDIA)
    if not (MEDIA / 'diabetes/board').exists():
        samples.dh_characters(L, MEDIA)
    if not (MEDIA / 'royal-oak/animatic/royal_oak_animatic.mp4').exists():
        samples.ro_animatic(L, S, MEDIA, ro_audio)
    if not (MEDIA / 'ep7/preview/ep7_full.mp4').exists():
        samples.ep7_preview(L, S, MEDIA)
    if not (MEDIA / 'timekeeper/logo.png').exists():
        samples.tk_board(S, MEDIA)
    if not (MEDIA / 'ep7/vo/l30.mp3').exists():
        samples.dh_voice(L, S, MEDIA)
    if not (MEDIA / 'looks/dark_keynote.jpg').exists():
        samples.looks(L, MEDIA)
    return L


def snapshot(extra_decisions=None) -> dict:
    S, _ = _scratch()
    vd = json.loads((ROOT / 'var/pages/voice-royal-oak/data.json').read_text(encoding='utf-8'))
    dd = json.loads((ROOT / 'var/pages/directions/data.json').read_text(encoding='utf-8'))
    return _build(log(), S, vd, dd, MEDIA, extra_decisions)


def locate(item: str):
    """project, video, scene for a review item id (used to file the decision event)."""
    if item.startswith('verdict-voice-'): return 'timekeeper', 'royal-oak', item.split('-')[2] + '-' + item.split('-')[3]
    if item.startswith('flag-tk-'): return 'timekeeper', 'royal-oak', None          # flag-tk-<line>-<word index>
    if item.startswith('flag-dh-'): return 'diabetes-history', 'ep7', None
    if item.startswith('voice-dh-'): return 'diabetes-history', 'ep6', None
    if item.startswith('voice-'): return 'timekeeper', 'royal-oak', item.split('-')[1] + '-' + item.split('-')[2]
    if item.startswith('art-ep7-'): return 'diabetes-history', 'ep7', item.split('-', 2)[2]
    if item.startswith('ep7-'): return 'diabetes-history', 'ep7', item.split('-')[1]          # gallery version ep7-<scene>-<v>
    if item.startswith('concept-ep7-'): return 'diabetes-history', 'ep7', item.split('-')[2]   # concept-ep7-<scene>-<technique>
    if item.startswith('task-voice-'): return 'timekeeper', 'royal-oak', item[len('task-voice-'):]
    if item.startswith('look-tk-'): return 'timekeeper', None, None
    if item.startswith('look-dh-'): return 'diabetes-history', None, None
    if item.startswith('f_'): return 'diabetes-history', 'ep7', None
    if item == 'final-ep7': return 'diabetes-history', 'ep7', None
    if item == 'direction-timekeeper' or item == 'eng-paper-banner': return 'timekeeper', None, None
    if item == 'direction-diabetes': return 'diabetes-history', None, None
    raise ValueError(f'unknown review item {item!r}')


SKELETON = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
            'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>{page}</body></html>')


def render_app(snap: dict, mode: str) -> str:
    """mode 'local': a complete document (doctype + mobile viewport), served by the local app.
    mode 'artifact': the page body only; the Artifact platform adds the same skeleton when it publishes."""
    html = TEMPLATE.read_text(encoding='utf-8')
    page = html.replace('__MODE__', mode).replace('__DATA__', json.dumps(snap, ensure_ascii=False).replace('</', '<\\/'))
    return SKELETON.replace('{page}', page) if mode == 'local' else page


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
