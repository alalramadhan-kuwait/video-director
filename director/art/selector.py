"""Art Director, part 1: recommend visual techniques per scene (rules, not a model).

A scene beat says what the narration needs to show:
    {id, beat, subject, accuracy: high|medium|low, assets: [...], max_cost: 0, real_person: bool,
     verified_photo: bool, note}
beat ∈ person_real, person_generic, product, detail, mechanism, place, journey, number, comparison,
       timeline, hook, quote, claim, document, background, action, establishing, transition

The selector returns ranked options with reasons and every exclusion with its reason, so the owner sees
why something was not offered. It never calls a generator and never spends anything.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import yaml

ACC = {'low': 0, 'medium': 1, 'high': 2}
ASSET_NEEDS = {  # what a technique cannot work without
    'archival_collage': {'photo', 'document', 'product_photo'},
    'product_macro': {'product_photo'},
    'live_footage': {'footage'},
    'verified_3d': {'3d_model'},
    'technical_illustration': {'technical_sheet', 'product_photo', 'photo'},
    'animated_timeline': {'dated_facts'},
    'scientific_diagram': {'data', 'source'},
    'ai_illustration': {'reference_images'},
}


def load_registry(path) -> dict:
    return {t['id']: t for t in yaml.safe_load(Path(path).read_text(encoding='utf-8'))['techniques']}


def recommend(scene: dict, profile: dict, registry: dict, n: int = 3) -> dict:
    beat = scene['beat']
    need_acc = ACC[scene.get('accuracy', 'high')]
    assets = set(scene.get('assets', []))
    max_cost = scene.get('max_cost', 0)
    art = profile.get('art', {})
    allowed, preferred = set(art.get('allowed', registry)), art.get('preferred', [])
    if beat == 'person_real' and not scene.get('verified_photo'):
        beat = 'person_real_no_photo'

    options, excluded = [], []
    for tid, t in registry.items():
        why_not = None
        if beat not in t['good_for'] and not (beat == 'person_real_no_photo' and tid == 'paper_cut'):
            continue
        if tid not in allowed:
            why_not = f'not in the {profile["id"]} profile'
        elif t['status'] == 'needs_code':
            why_not = 'needs engine work first'
        elif t['cost'] == 'paid' and max_cost == 0:
            why_not = 'paid technique and this scene has no budget'
        elif tid == 'ai_illustration' and (scene.get('real_person') or beat in ('product', 'detail', 'mechanism')):
            why_not = 'AI is never used for real people, real products or established mechanisms'
        elif beat == 'person_real_no_photo' and tid in ('character_animation', 'ai_illustration', 'parallax_25d'):
            why_not = 'no verified photo: never invent a face'
        elif ACC[t['accuracy']] < need_acc - 1:
            why_not = f"{t['accuracy']} accuracy for a {scene.get('accuracy', 'high')}-accuracy scene"
        if why_not:
            excluded.append({'technique': tid, 'reason': why_not}); continue

        score, reasons, warnings = 0.0, [], []
        if tid in preferred:
            score += 3 - preferred.index(tid) * 0.5; reasons.append('preferred by the profile')
        if beat in t['good_for']:
            score += 2; reasons.append(f'suited to a {beat.replace("_", " ")} beat')
        if ACC[t['accuracy']] >= need_acc:
            score += 1
        else:
            score -= 1; warnings.append(f"{t['accuracy']} accuracy: use as a supporting layer, not as evidence")
        need = ASSET_NEEDS.get(tid)
        if need and not (need & assets):
            score -= 2.5; warnings.append('missing assets: ' + ' or '.join(sorted(need)))
        if beat == 'person_real_no_photo' and tid == 'neutral_placeholder':
            score += 5; reasons.append('no documented photo: labelled placeholder, never an invented face')
        options.append({'technique': tid, 'name': t['name'], 'score': round(score, 2), 'reasons': reasons,
                        'warnings': warnings, 'risks': t['risks'], 'cost': t['cost']})
    options.sort(key=lambda o: -o['score'])
    return {'scene': scene['id'], 'beat': beat, 'options': options[:max(n, 1)], 'more': len(options) > n,
            'excluded': excluded, 'enough_options': len(options) >= n}


def record_choice(log_path, project, scene_id, chosen, rejected: list[dict], by='owner', reason=''):
    """Decision history: what was chosen, what was rejected and why (used later to suggest better designs).
    Stored per project, so one project's taste never becomes another project's rule."""
    row = {'project': project, 'scene': scene_id, 'chosen': chosen, 'rejected': rejected, 'by': by, 'reason': reason,
           'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row
