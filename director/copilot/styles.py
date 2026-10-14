"""Style registry (art/styles.yaml) and Gate 4 boards: real frames of THIS film's scenes drawn in each style.

A board is three of the project's own scenes (the opening, a mechanism, a place or product beat) rendered by the
same engine and the same scene builder the film uses, so what the owner approves is what the scenes will look like.
"""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

import yaml

from ..studio import art, engine

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'art/styles.yaml'


def registry() -> dict:
    d = yaml.safe_load(REGISTRY.read_text(encoding='utf-8'))
    for s in d['styles']:
        s['params_hash'] = hashlib.sha256(json.dumps(s, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return d


def get(style_id, version=None) -> dict | None:
    return next((s for s in registry()['styles'] if s['id'] == style_id and (version is None or s['version'] == version)), None)


def choose(style: dict, bs: dict, verified: dict, hook_visual: dict | None = None) -> dict:
    """Which technique draws this brief scene in this style. `verified` = {asset slot: asset} the project may use.
    Returns {technique, params, theme, fallback (why), assets}."""
    if hook_visual:
        t, p = hook_visual['technique'], hook_visual['params']
        return {'technique': t, 'params': p, 'theme': style.get('theme_for', {}).get(t, style['theme']), 'fallback': None, 'assets': []}
    concepts = bs.get('concepts', {})
    def usable(t):
        if t not in art.BUILDERS or t == 'neutral_placeholder' or t not in concepts: return False
        need = art.NEEDS_ASSETS.get(t, lambda p: [])(concepts[t])
        return all(n in verified for n in need)
    for t in style['prefer']:
        if usable(t):
            need = art.NEEDS_ASSETS.get(t, lambda p: [])(concepts[t])
            return {'technique': t, 'params': concepts[t], 'theme': style.get('theme_for', {}).get(t, style['theme']), 'fallback': None, 'assets': need}
    beat = bs.get('beat')
    photo = next((a for a in verified.values() if a.get('scene') == bs.get('_id') and a['use'] == 'evidence'), None)
    if beat == 'person_real' and photo:
        p = {'photos': [{'asset': photo['slot'], 'desc': photo.get('what') or photo.get('name', ''), 'label': bs.get('banner') or '', 'w': 480, 'y': 560}]}
        return {'technique': 'archival_collage', 'params': p, 'theme': style['theme'], 'fallback': None, 'assets': [photo['slot']]}
    if usable(bs.get('default', '')):
        t = bs['default']
        return {'technique': t, 'params': concepts[t], 'theme': style.get('theme_for', {}).get(t, style['theme']), 'fallback': None, 'assets': []}
    name = bs.get('banner') or ''
    why = ('no licensed photograph of this person in the project: a name card instead (no picture is invented)' if beat == 'person_real'
           else 'the techniques for this scene need material the project does not have: a type card instead')
    return {'technique': 'kinetic_type', 'params': {'lines': [{'text': name or '…', 'size': 92, 'in': 'fade', 'at': 0.2}], 'y': 600},
            'theme': style['theme'], 'fallback': why, 'assets': [], 'banner_off': bool(name)}


def representative(brief: dict, order: list[str], verified=None) -> list[str]:
    """The opening, then the two scenes where the ready styles differ most (so the boards show the real difference)."""
    ready = [s for s in registry()['styles'] if s['status'] == 'ready']
    def spread(sid):
        bk = sid if sid in brief['scenes'] else 'h'
        cs = [choose(s, {**brief['scenes'][bk], '_id': sid}, verified or {}) for s in ready]
        return len({(c['technique'], c['theme']) for c in cs}), len({c['technique'] for c in cs})
    rest = sorted(order[1:], key=lambda s: (-spread(s)[1], -spread(s)[0], order.index(s)))
    picks = [order[0]]
    for s in rest:
        if len(picks) >= 3: break
        if brief['scenes'].get(s, {}).get('beat') not in [brief['scenes'].get(p, {}).get('beat') for p in picks[1:]]: picks.append(s)
    for s in rest:
        if len(picks) >= 3: break
        if s not in picks: picks.append(s)
    return picks


def board(studio, pid, style: dict, brief: dict, order: list[str], hook_visual, verified, brand, work: Path) -> dict:
    """Draw the board: one frame per representative scene (at 60 % of the scene, after its entrance), side by side."""
    ids = representative(brief, order, verified)
    scenes, times, t = [], [], 0.0
    for sid in ids:
        bs = {**brief['scenes'][sid if sid in brief['scenes'] else 'h'], '_id': sid}
        c = choose(style, bs, verified, hook_visual if sid == order[0] else None)
        dur = bs.get('dur', 5.0)
        p = c['params']
        if style.get('text_scale', 1.0) != 1.0:
            p, _ = art.apply_changes(p, c['theme'], {'text_size': style['text_scale']})
        sc = art.scene_visual(c['technique'], p, c['theme'], dur, None if (sid == order[0] or c.get('banner_off')) else bs.get('banner'))
        scenes.append({**sc, 'dur': dur})
        times.append(t + dur * 0.6); t += dur
    sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style(brand), 'scenes': scenes}
    files = engine.stills(sb, work, times, scale=0.35)
    stills = [studio.put_file(pid, f, 'png') for f in files]
    out = work / 'board.png'
    files = files[::-1]                                       # right to left, as the Arabic film reads: the opening on the right
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *sum((['-i', str(f)] for f in files), []), '-filter_complex',
                    ''.join(f'[{i}:v]' for i in range(len(files))) + f'hstack=inputs={len(files)}', str(out)], check=True)
    return {'board': studio.put_file(pid, out, 'png'), 'stills': stills, 'scenes': ids}
