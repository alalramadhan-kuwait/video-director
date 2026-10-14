"""One read-only snapshot of production state for the dashboard (v2: studio layout).

Everything here is READ from the existing components; nothing is generated, written to a profile, or sent to a
provider. This module does not import the paid gateway, and no value in the snapshot can start a paid call.

Rules kept on purpose:
  * every completion figure is a count of real units; no weighted or guessed percentages;
  * stage status comes from the latest stage_status event, or from live counts where a stage has them;
  * unknown stays unknown; nothing is estimated that the event log cannot back;
  * art concepts are PROPOSALS. A concept preview is either a real reference from another scene of the same series
    (labelled so) or absent; nothing is shown as if it had been drawn for the scene;
  * voice IDs, consent records and keys are never copied into the snapshot.
"""
from __future__ import annotations
import hashlib, json, os, time
from collections import Counter, defaultdict
from pathlib import Path
import yaml

from .. import profiles
from ..events import EventLog
from ..ledger import Ledger
from ..art.selector import load_registry, recommend, ASSET_NEEDS

ROOT = Path(__file__).resolve().parents[2]
STAGES = ['script', 'hook', 'voice', 'art', 'render', 'final', 'publish']
STAGE_LABEL = {'script': 'Script', 'hook': 'Hook', 'voice': 'Voice', 'art': 'Art', 'render': 'Render',
               'final': 'Final video', 'publish': 'Publish'}
ACTIVE = ('blocked', 'failed', 'processing', 'waiting_review')
SEV_ORDER = {'critical': 0, 'major': 1, 'minor': 2, 'info': 3}
FACTUAL = {'Historical and technical accuracy', 'Correct watches, products and people', 'Does the image match the narration?'}
FIXABLE = {'Composition and visual hierarchy', 'Readability of Arabic text', 'Lighting, colours and character proportions'}
# where each technique can be SEEN in this series already (real frames from the published episode 7)
DH_REFERENCE = {'paper_cut': 'a1', 'character_animation': 'a4', 'scientific_diagram': 'b3', 'animated_timeline': 'd1',
                'kinetic_type': 'k1', 'map': 'd3'}


def _decisions(log: EventLog) -> dict:
    out = {}
    for r in log.rows(kind='review_decided'):
        out[r['data'].get('item')] = {'decision': r['status'], 'note': r['data'].get('note', ''), 'at': r['at'],
                                      'by': r['actor'], 'event': r['seq'], 'locked': r['status'] == 'approved'}
    return out


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------- stages
def _stage_block(log: EventLog, project, video, live_units: dict) -> list[dict]:
    rows = [r for r in log.rows(project=project) if r['video'] == video]
    out = []
    for st in STAGES:
        sr = [r for r in rows if r['stage'] == st]
        status_ev = [r for r in sr if r['kind'] == 'stage_status']
        status = status_ev[-1]['status'] if status_ev else 'unknown'
        why = status_ev[-1]['data'].get('why') if status_ev else 'no event recorded'
        units = live_units.get(st)
        if units and units.get('override'):
            status, why = units['override'], units.get('why', why)
        out.append({'stage': st, 'label': STAGE_LABEL[st], 'status': status, 'why': why,
                    'units': {k: units[k] for k in ('done', 'total', 'unit') if units and k in units} or None,
                    'first_activity': min((r['at'] for r in sr if r['kind'] != 'stage_status'), default=None),
                    'approved_at': status_ev[-1]['at'] if status == 'approved' and status_ev else None,
                    'source': status_ev[-1]['source'] if status_ev else None,
                    'evidence': status_ev[-1]['evidence'] if status_ev else None})
    return out


def _current_stage(stages):
    act = next((s for s in stages if s['status'] in ACTIVE), None)
    if act:
        return {'stage': act['stage'], 'label': act['label'], 'status': act['status'], 'why': act['why']}
    appr = [s for s in stages if s['status'] == 'approved']
    if appr:
        return {'stage': appr[-1]['stage'], 'label': appr[-1]['label'], 'status': 'approved', 'why': appr[-1]['why']}
    return {'stage': None, 'label': 'Not recorded', 'status': 'unknown', 'why': 'no stage has a recorded status'}


def _history(log: EventLog, project, video, scene=None):
    out = []
    for r in log.rows(project=project):
        if r['video'] != video or r['kind'] not in ('revision', 'review_decided', 'stage_status', 'task_finished', 'task_failed', 'blocked'):
            continue
        if scene is not None and r['scene'] != scene:
            continue
        out.append({'at': r['at'], 'kind': r['kind'], 'stage': r['stage'], 'scene': r['scene'], 'status': r['status'],
                    'what': r['data'].get('what') or r['data'].get('why') or r['task'] or r['data'].get('note') or '',
                    'source': r['source'], 'evidence': r['evidence'], 'actor': r['actor'], 'event': r['seq']})
    return sorted(out, key=lambda e: e['at'])


# ---------------------------------------------------------------------------------------------------- findings
def classify(f) -> str:
    """Which kind of review work a finding is (the inbox buckets). Works on report findings (dimension_label)."""
    dim = f.get('dimension_label') or f.get('dimension')
    if any('without a cited fact' in n for n in f.get('notes', [])):
        return 'blocked'                       # a factual claim nobody has a source for yet
    if dim in FACTUAL:
        # it changes what the film says or shows: yours to decide, unless it is a minor, low-confidence remark
        return 'suggestion' if f['severity'] in ('minor', 'info') and f.get('confidence') == 'low' else 'decide'
    if dim in FIXABLE and (f['severity'] in ('critical', 'major') or dim != 'Lighting, colours and character proportions'):
        return 'fixable'                       # layout / readability: no change to narration, audio or facts
    if f['severity'] in ('critical', 'major'):
        return 'decide'                        # a major creative point (style, motion)
    return 'suggestion'


BUCKET_LABEL = {'decide': 'Needs your decision', 'fixable': 'Claude can fix without changing approved content',
                'suggestion': 'Suggestion only', 'blocked': 'Blocked by missing evidence or assets'}


def _finding_view(f, decisions):
    return {'id': f['id'], 'scene': f['scene'], 't': f['t'], 'timecode': f['timecode'], 'source': f['source'],
            'dimension': f['dimension_label'], 'severity': f['severity'], 'confidence': f['confidence'],
            'problem': f['problem'], 'suggestion': f['suggestion'], 'notes': f['notes'], 'bucket': classify(f),
            'evidence': [e for e in f['evidence'] if e.get('kind') in ('fact', 'measurement')],
            'frames': [e['ref'] for e in f['evidence'] if e.get('kind') in ('still', 'strip')],
            'reviewer': f.get('reviewer'), 'decision': decisions.get(f['id'])}


# ---------------------------------------------------------------------------------------------------- concepts
_LOOK_SAMPLES: set = set()          # prototype looks with a code-made sample in media/looks (set by build())


def _look_sample(tid, scene_id=None):
    if tid not in _LOOK_SAMPLES:
        return None
    where = f'not drawn for {scene_id}' if scene_id else 'not tied to a scene'
    return {'kind': 'sample', 'img': f'media/looks/{tid}.jpg', 'clip': f'media/looks/{tid}',
            'label': f'Sample of this look, made here in the brand colours · {where}.'}


def _concepts(beat, prof, registry, facts, scene_findings, decisions, scene_id, refs_available):
    if not beat:
        return {'note': 'no beat written for this scene', 'options': [], 'recommended': None}
    r = recommend(beat, prof, registry, n=4)
    have = set(beat.get('assets') or [])
    out = []
    for i, o in enumerate(r['options']):
        t = registry[o['technique']]
        need = ASSET_NEEDS.get(o['technique'])
        renderable = t['status'] == 'available' and (not need or bool(need & have))
        ref = DH_REFERENCE.get(o['technique'])
        preview = None
        if t['status'] == 'prototype':
            preview = _look_sample(o['technique'], scene_id)
        elif ref and ref in refs_available:
            preview = {'kind': 'reference', 'scene': ref, 'img': f'media/ep7/stills/{ref}.jpg',
                       'clip': f'media/ep7/clips/{ref}', 'label': f'Reference: how this looks in scene {ref} of this episode. Not drawn for {scene_id}.'}
        risks = [t['risks']] + [f['problem'] for f in scene_findings if f['dimension_label'] in FACTUAL][:2]
        cid = f"concept-ep7-{scene_id}-{o['technique']}"
        out.append({'id': cid, 'technique': o['technique'], 'name': o['name'], 'kind': 'proposal',
                    'recommended': i == 0, 'score': o['score'], 'reasons': o['reasons'], 'warnings': o['warnings'],
                    'strengths': t.get('strengths'), 'limitations': t.get('limits'), 'risks': [x for x in risks if x],
                    'required_assets': {'needs': sorted(need) if need else [], 'note': t.get('assets'),
                                        'have': sorted(have), 'missing': sorted(need - have) if need and not (need & have) else []},
                    'sources': [f for f in facts if f['id'] in (beat.get('facts') or [])],
                    'renderable': renderable,
                    'renderable_why': ('renderable now with free local tools' if renderable else
                                       'prototype: a sample exists, not in the production engine yet' if t['status'] == 'prototype' else
                                       'needs engine work first' if t['status'] != 'available' else
                                       'missing: ' + ' or '.join(sorted(need))),
                    'cost': t['cost'], 'support': t.get('support'), 'preview': preview, 'decision': decisions.get(cid)})
    return {'beat': r['beat'], 'objective': beat.get('objective'), 'note': 'Proposals from the Art Director. Text only unless a reference image is shown; nothing has been drawn or generated.',
            'options': out, 'recommended': out[0]['technique'] if out else None, 'excluded': r['excluded']}


def _versions_ep7(scene, log, decisions):
    final = {'id': f'ep7-{scene}-final', 'label': 'Published render', 'img': f'media/ep7/stills/{scene}.jpg',
             'clip': f'media/ep7/clips/{scene}', 'what': 'In the published episode (draft until you approve it)',
             'source': 'ep7 render, 2026-10-12', 'cost': 'free (local render)', 'decision': decisions.get(f'ep7-{scene}-final')}
    if scene != 'b1':
        return [final]
    revs = {r['evidence']: r['at'] for r in log.rows(project='diabetes-history', scene='b1', kind='revision')}
    spec = [('A', 'b1_v1', 'chk/p2b.png', 'Chip «مدة أطول» hidden under the caption'),
            ('B', 'b1_v2', 'chk/p2c.png', 'Doctor name over the year card'),
            ('C', 'b1_v3', 'chk/p2d.png', 'Name and chip clear (this is what was published)')]
    return [{'id': f'ep7-b1-{v}', 'label': f'Revision {lab}', 'img': f'media/ep7/revisions/{v}.jpg',
             'clip': 'media/ep7/clips/b1' if lab == 'C' else None, 'what': what,
             'source': f'render check {src}, {revs.get(f"file time: ep7/{src}", "")[11:16]} UTC 12 Oct',
             'cost': 'free (local render)', 'decision': decisions.get(f'ep7-b1-{v}')} for lab, v, src, what in spec]


# ---------------------------------------------------------------------------------------------------- videos
def diabetes_ep7(log, S: Path, decisions: dict, registry, prof):
    pack = json.loads((ROOT / 'var/review/ep7-final/pack.json').read_text(encoding='utf-8'))
    ev = yaml.safe_load((ROOT / 'art/evidence/diabetes-ep7.yaml').read_text(encoding='utf-8'))
    rep = json.loads((ROOT / 'var/review/ep7-final/artistic_report.json').read_text(encoding='utf-8'))
    beats = {b['id']: b for b in yaml.safe_load((ROOT / 'art/beats/diabetes-ep7.yaml').read_text(encoding='utf-8'))['scenes']}
    by_scene = defaultdict(list)
    for f in rep['ai_judgement'] + rep['automated']:
        by_scene[f['scene']].append(f)
    ids = {s['id'] for s in pack['scenes']}
    scenes = []
    for s in pack['scenes']:
        m = ev['scenes'].get(s['id'], {})
        fs = by_scene.get(s['id'], [])
        views = [_finding_view(f, decisions) for f in sorted(fs, key=lambda f: (SEV_ORDER[f['severity']], f['t']))]
        open_f = [f for f in views if not f['decision']]
        versions = _versions_ep7(s['id'], log, decisions)
        approved = next((v for v in versions if v['decision'] and v['decision']['decision'] == 'approved'), None)
        verdict = (decisions.get(f"art-ep7-{s['id']}") or {}).get('decision')     # the whole scene: approved / changes_requested
        scenes.append({
            'id': s['id'], 'start': round(s['start'], 2), 'end': round(s['end'], 2), 'dur': round(s['end'] - s['start'], 2),
            'narration': m.get('narration'), 'objective': (beats.get(s['id']) or {}).get('objective'), 'plan': m.get('plan'),
            'on_screen_text': m.get('on_screen_text') or [], 'thumb': f"media/ep7/stills/{s['id']}.jpg",
            'clip': f"media/ep7/clips/{s['id']}",
            'selected_version': ({'label': approved['label'], 'state': 'approved'} if approved else
                                 {'label': 'Published render', 'state': 'draft'}),
            'art_status': ('approved' if approved or verdict == 'approved' else 'changes' if verdict == 'changes_requested'
                           else 'waiting_review' if views else 'no_findings'),
            'severity': min((f['severity'] for f in open_f), key=lambda x: SEV_ORDER[x], default=None),
            'findings': views, 'findings_open': len(open_f), 'render': {'state': 'rendered', 'source': 'published file'},
            'concepts': _concepts(beats.get(s['id']), prof, registry, ev['facts'], fs, decisions, s['id'], ids),
            'versions': versions, 'history': _history(log, 'diabetes-history', 'ep7', s['id'])})
    reviewed = [x for x in scenes if x['art_status'] in ('approved', 'changes')]
    live = {'art': {'done': len(reviewed), 'total': len(scenes), 'unit': 'scenes reviewed'},
            'voice': {'done': 30, 'total': 30, 'unit': 'narration lines approved'},
            'render': {'done': 5, 'total': 5, 'unit': 'output files rendered'}}
    if scenes and all(x['art_status'] == 'approved' for x in scenes):
        live['art'].update(override='approved', why='every scene approved')
    stages = _stage_block(log, 'diabetes-history', 'ep7', live)
    return {'id': 'ep7', 'project': 'diabetes-history', 'series': 'قصة السكري', 'episode': 'Episode 7 of 10',
            'title': '«إبرة أقل»', 'title_en': 'One needle less', 'duration': round(pack['meta']['duration'], 2),
            'platform': 'TikTok · 1080×1920',
            'preview': {'kind': 'render', 'mp4': 'media/ep7/preview/ep7_full.mp4', 'webm': 'media/ep7/preview/ep7_full.webm',
                        'poster': 'media/ep7/stills/a1.jpg',
                        'label': 'The published episode (re-encoded to 540×960 for this dashboard; the original file is untouched).'},
            'stages': stages, 'current_stage': _current_stage(stages), 'scenes': scenes,
            'facts': ev['facts'], 'history': _history(log, 'diabetes-history', 'ep7')}


def royal_oak(log, S: Path, decisions: dict, voice_data: dict):
    R = S / 'audit/claude_success-story-video/video/royal-oak'
    ro_style = json.loads((R / 'ro-style.json').read_text(encoding='utf-8'))
    lines = {l['id']: l for l in voice_data['lines']}
    scenes, t = [], 0.0
    for part in (1, 2, 3):
        p = json.loads((R / f'part{part}.json').read_text(encoding='utf-8'))
        for i, s in enumerate(p['scenes'], 1):
            sid = f'P{part}-{i:02d}'
            line = Path(s.get('voice') or '').stem or None
            l = lines.get(line)
            qs = [q for q in (l['questions'] if l else []) if q['common_noun']]
            answered = [q for q in qs if _confirmed(decisions.get(f"voice-{q['key']}"))]
            scenes.append({'id': sid, 'part': part, 'start': round(t, 2), 'end': round(t + s['dur'], 2), 'dur': s['dur'],
                           'narration': (l or {}).get('approved_text') or s.get('captions', '').replace(' | ', ' '),
                           'objective': None, 'voice_line': line, 'theme': s.get('theme'),
                           'theme_bg': ro_style['themes'].get(s.get('theme'), {}).get('bg'),
                           'thumb': f'media/royal-oak/animatic/frames/{sid}.jpg', 'thumb_kind': 'animatic',
                           'audio': f'media/royal-oak/audio/{line}.mp3' if line else None,
                           'endcard': s.get('endcard') == 'timekeeper',
                           'voice_status': 'approved' if l and l['plan']['action'] == 'reuse' else ('none' if not line else 'unknown'),
                           'listening': {'asked': len(qs), 'answered': len(answered)},
                           'selected_version': {'label': 'No artwork in this workspace', 'state': 'missing'},
                           'art_status': 'unknown', 'severity': None, 'findings': [], 'findings_open': 0,
                           'render': {'state': 'not here', 'source': 'no render file in this workspace'},
                           'versions': [], 'concepts': {'note': 'No scene beats written for Royal Oak yet, so the Art Director has no concepts to propose.', 'options': []},
                           'history': []})
            t += s['dur']
    q_items = [q for l in voice_data['lines'] for q in l['questions'] if q['common_noun']]
    answered = sum(1 for q in q_items if _confirmed(decisions.get(f"voice-{q['key']}")))
    n_lines = len({l['id'] for l in voice_data['lines'] if any(q['common_noun'] for q in l['questions'])})
    live = {'voice': {'done': answered, 'total': len(q_items), 'unit': f'listening checks answered ({n_lines} lines)'}}
    if q_items and answered == len(q_items):
        live['voice'].update(override='approved', why='all listening checks answered')
    stages = _stage_block(log, 'timekeeper', 'royal-oak', live)
    return {'id': 'royal-oak', 'project': 'timekeeper', 'series': 'Time Keeper films', 'episode': 'Royal Oak · parts 1–3',
            'title': 'Royal Oak', 'title_en': 'The Royal Oak story', 'duration': round(t, 2), 'platform': '1080×1920',
            'preview': {'kind': 'animatic', 'mp4': 'media/royal-oak/animatic/royal_oak_animatic.mp4',
                        'webm': 'media/royal-oak/animatic/royal_oak_animatic.webm', 'poster': 'media/royal-oak/animatic/frames/P1-01.jpg',
                        'label': 'Animatic made here: the storyboard text on its theme colours with the approved narration. '
                                 'Not the film; its photographs and renders are not in this workspace.'},
            'stages': stages, 'current_stage': _current_stage(stages), 'scenes': scenes, 'facts': [],
            'history': _history(log, 'timekeeper', 'royal-oak')}


def _confirmed(d):
    return bool(d) and d['decision'] in ('article_heard', 'article_missing', 'heard_english', 'heard_other', 'unsure')


def _bare(written: str) -> str:
    """The phrase without the Arabic article: «الذهب الأبيض» -> «ذهب أبيض», «بالكوارتز» -> «كوارتز»."""
    out = []
    for w in written.split():
        for pre in ('بال', 'فال', 'وال', 'ال'):
            if w.startswith(pre) and len(w) > len(pre) + 1:
                w = w[len(pre):]; break
        out.append(w)
    return ' '.join(out)


FLAG_TYPES = {'wrong': 'Wrong pronunciation', 'english': 'Said in English', 'article': 'Missing «الـ»',
              'vowel': 'Wrong vowel or stress', 'unclear': 'Unclear or swallowed', 'other': 'Something else'}


def voice_lines(voice_data, ro, S: Path, decisions):
    """Every narration line with its audio and word timings, for listening and flagging words."""
    out = {'timekeeper': [], 'diabetes-history': []}
    scene_of = {s['voice_line']: s['id'] for s in ro['scenes'] if s.get('voice_line')}
    for l in voice_data['lines']:
        out['timekeeper'].append({'id': l['id'], 'scene': scene_of.get(l['id']), 'text': l['approved_text'],
                                  'audio': f"media/royal-oak/audio/{l['id']}.mp3",
                                  'words': [{'w': w['w'], 's': w['s'], 'e': w['e']} for w in l['takes'][0]['words']]})
    for part in ('p1', 'p2', 'p3'):
        tl = json.loads((S / f'ep7/{part}/timeline.json').read_text(encoding='utf-8'))
        proj = json.loads((S / f'ep7/{part}/project.json').read_text(encoding='utf-8'))
        scene_of = {lid: sc['id'] for sc in proj['scenes'] for lid in sc.get('lines', [])}
        for v in tl['vo']:
            out['diabetes-history'].append({'id': v['id'], 'scene': scene_of.get(v['id']), 'text': v['text'],
                                            'audio': f"media/ep7/vo/{v['id']}.mp3",
                                            'words': [{'w': w.get('w') or w.get('text'), 's': round(w['s'] - v['start'], 3),
                                                       'e': round(w['e'] - v['start'], 3)} for w in v['words']]})
    return out


def flags(lines, decisions):
    """Words the owner flagged while listening (latest decision 'flagged'; 'dismissed' removes a flag)."""
    out = {}
    for pk, short in (('timekeeper', 'tk'), ('diabetes-history', 'dh')):
        out[pk] = []
        for l in lines[pk]:
            for i, w in enumerate(l['words']):
                d = decisions.get(f"flag-{short}-{l['id']}-{i}")
                if d and d['decision'] == 'flagged':
                    kind, _, note = (d.get('note') or 'other').partition(':')
                    out[pk].append({'item': f"flag-{short}-{l['id']}-{i}", 'line': l['id'], 'scene': l['scene'], 'index': i,
                                    'word': w['w'], 's': w['s'], 'e': w['e'], 'type': kind.strip(),
                                    'type_label': FLAG_TYPES.get(kind.strip(), kind.strip()), 'note': note.strip(), 'at': d['at'],
                                    'decision': d})
    return out


# ---------------------------------------------------------------------------------------------------- review tasks
def listening_checks(voice_data, media: Path, decisions):
    out = []
    for l in voice_data['lines']:
        take = l['takes'][0]
        for q in l['questions']:
            if not q['common_noun']:
                continue
            f = media / 'royal-oak/audio' / f"{l['id']}.mp3"
            ws = take['words'][q['words'][0]]['s']; we = take['words'][q['words'][-1]]['e']
            out.append({'id': f"voice-{q['key']}", 'line': l['id'], 'written': q['written'], 'sent': q['sent'],
                        'without_article': _bare(q['written']), 'verdict': decisions.get(f"verdict-voice-{q['key']}"),
                        'audio': f"media/royal-oak/audio/{l['id']}.mp3", 'audio_file': f"{l['id']}.mp3",
                        'available': f.exists(), 'sha256': _sha(f) if f.exists() else None,
                        'duration': take['duration'], 'word_s': ws, 'word_e': we,
                        'cost_if_changed': (l['corrections'] or {}).get('keep_arabic', {}).get('chars'),
                        'decision': decisions.get(f"voice-{q['key']}")})
    return out


def review_tasks(ep7, ro, checks, decisions, directions_data):
    tasks = []
    by_line = defaultdict(list)
    for c in checks:
        by_line[c['line']].append(c)
    for line, cs in by_line.items():
        done = [c for c in cs if _confirmed(c['decision'])]
        scene = next((s['id'] for s in ro['scenes'] if s['voice_line'] == line), None)
        tasks.append({'id': f'task-voice-{line}', 'type': 'voice', 'project': 'timekeeper', 'video': 'royal-oak', 'scene': scene,
                      'title': f'Listen to line {line}: ' + ', '.join(f'«{c["written"]}»' for c in cs),
                      'status': 'done' if len(done) == len(cs) else ('blocked' if not all(c['available'] for c in cs) else 'needs_decision'),
                      'priority': 'listening', 'checks': cs, 'progress': {'done': len(done), 'total': len(cs)},
                      'why': 'Text check: the article was not sent to the voice. Only listening decides whether it is heard.',
                      'notes': ['Git 46ddf9e (12 Oct): “quartz and steel voiced with the article” in the Part 2 hook.']})
    for s in ep7['scenes']:
        if not s['findings']:
            continue
        b = Counter(f['bucket'] for f in s['findings'] if not f['decision'])
        verdict = (decisions.get(f"art-ep7-{s['id']}") or {}).get('decision')
        status = ('done' if not sum(b.values()) or verdict in ('approved', 'changes_requested') else 'needs_decision' if b['decide'] else 'blocked' if b['blocked']
                  else 'fixable' if b['fixable'] else 'suggestion')
        top = sorted(s['findings'], key=lambda f: SEV_ORDER[f['severity']])
        tasks.append({'id': f"art-ep7-{s['id']}", 'type': 'art', 'project': 'diabetes-history', 'video': 'ep7', 'scene': s['id'],
                      'title': f"Scene {s['id']}: review the art",
                      'status': status, 'priority': top[0]['severity'], 'buckets': dict(b),
                      'findings': s['findings'], 'progress': {'done': len(s['findings']) - sum(b.values()), 'total': len(s['findings'])},
                      'why': top[0]['problem'], 'decision': decisions.get(f"art-ep7-{s['id']}")})
    open_art = sum(1 for t in tasks if t['type'] == 'art' and t['status'] != 'done')
    fixes = sum(1 for s in ep7['scenes'] if s['art_status'] == 'changes')
    final_dec = decisions.get('final-ep7')
    tasks.append({'id': 'final-ep7', 'type': 'final', 'project': 'diabetes-history', 'video': 'ep7', 'scene': None,
                  'title': 'Approve the final episode 7 video',
                  'status': 'done' if final_dec and final_dec['decision'] == 'approved' else 'blocked' if open_art or fixes else 'needs_decision',
                  'priority': 'decision',
                  'blocked_by': (f'{open_art} scenes still to review' if open_art else f'{fixes} scenes waiting for fixes' if fixes else None),
                  'why': 'Publishing also stays blocked until the Fasih licence (CPML) is reviewed (your Phase 0.5 decision).',
                  'decision': decisions.get('final-ep7')})
    for pk, title in (('timekeeper', 'Time Keeper'), ('diabetes', 'Diabetes History')):
        iid = f'direction-{pk}'
        tasks.append({'id': iid, 'type': 'direction', 'project': 'timekeeper' if pk == 'timekeeper' else 'diabetes-history',
                      'video': None, 'scene': None, 'title': f'{title}: choose a creative direction', 'priority': 'decision',
                      'status': 'done' if decisions.get(iid) else 'needs_decision',
                      'why': 'Three proposals; the profile stays a draft until you approve it separately: '
                             + ', '.join(d['name'] for d in directions_data['projects'][pk]['directions']),
                      'decision': decisions.get(iid)})
    tasks.append({'id': 'eng-paper-banner', 'type': 'engineering', 'project': 'timekeeper', 'video': None, 'scene': None,
                  'title': 'Allow a fix to the paper-story checker (production code)', 'priority': 'major',
                  'status': 'done' if decisions.get('eng-paper-banner') else 'needs_decision',
                  'why': 'engine/paper.css line 38 gives the banner zero size, so nothing under it is ever reported.',
                  'decision': decisions.get('eng-paper-banner')})
    tasks.append({'id': 'voice-dh-ep6-insulin', 'type': 'voice', 'project': 'diabetes-history', 'video': 'ep6', 'scene': None,
                  'title': 'Episode 6: «الإنسولين» lines, re-listen or re-voice', 'priority': 'listening',
                  'status': 'done' if decisions.get('voice-dh-ep6-insulin') else 'blocked',
                  'blocked_by': 'the episode 6 audio and review data are not loaded in this dashboard yet',
                  'why': 'Open from an earlier review.', 'decision': decisions.get('voice-dh-ep6-insulin')})
    return tasks


PRIORITY = {'critical': 0, 'major': 1, 'listening': 2, 'decision': 3, 'minor': 4, 'info': 5}


def next_action(tasks, project):
    cand = [t for t in tasks if t['project'] == project and t['status'] in ('needs_decision', 'fixable')]
    cand.sort(key=lambda t: (t['status'] != 'needs_decision', t['video'] is None, PRIORITY.get(t['priority'], 9)))
    return cand[0] if cand else None


def brand_looks(project, prof, registry, decisions):
    """The prototype looks this brand's profile allows, with their samples. Proposals: choosing one is not approving art."""
    short = 'tk' if project == 'timekeeper' else 'dh'
    out = []
    for tid in (prof.get('art') or {}).get('allowed', []):
        t = registry.get(tid)
        if not t or t['status'] != 'prototype':
            continue
        need = ASSET_NEEDS.get(tid)
        iid = f'look-{short}-{tid}'
        out.append({'id': iid, 'technique': tid, 'name': t['name'], 'kind': 'proposal', 'status': t['status'],
                    'good_for': t['good_for'], 'strengths': t.get('strengths'), 'limitations': t.get('limits'), 'risks': [t['risks']],
                    'required_assets': {'needs': sorted(need) if need else [], 'note': t.get('assets')},
                    'inspired_by': t.get('inspired_by'), 'cost': t['cost'], 'renderable': False,
                    'renderable_why': 'prototype: a sample exists, not in the production engine yet',
                    'preview': _look_sample(tid), 'decision': decisions.get(iid)})
    return out


# ---------------------------------------------------------------------------------------------------- costs
def costs(registry, voice_data, ledger: Ledger, S: Path):
    base = json.loads((S / 'phase05/elevenlabs_baseline.json').read_text(encoding='utf-8'))
    ops = [{'op': 'Render (paper story, motion, ad engine)', 'kind': 'free', 'where': 'local'},
           {'op': 'Previews, animatic, evidence packs, checks', 'kind': 'free', 'where': 'local'},
           {'op': 'Word timing (faster-whisper)', 'kind': 'free', 'where': 'local'},
           {'op': 'Diabetes narration (Fasih + Bram)', 'kind': 'free', 'where': 'local · publishing blocked until licence review'},
           {'op': 'Draft narration for timing (gTTS)', 'kind': 'free', 'where': 'online, drafts only'},
           {'op': 'Time Keeper final narration (ElevenLabs)', 'kind': 'paid', 'where': 'locked behind the gateway'},
           {'op': 'AI illustration (fal.ai / Higgsfield)', 'kind': 'paid', 'where': 'not offered: no budget, never for real people or products'},
           {'op': 'AI art review in the product (model API)', 'kind': 'paid', 'where': 'not built; in development it runs in a separate session'}]
    for t in registry.values():
        ops.append({'op': f"Art technique: {t['name']}", 'kind': 'paid' if t['cost'] == 'paid' else 'free', 'where': 'registry: ' + t['status']})
    corr = sum((l['corrections'] or {}).get('keep_arabic', {}).get('chars', 0) for l in voice_data['lines'] if l['queue'])
    enabled = os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') == '1'
    return {'operations': ops,
            'providers': [{'project': 'timekeeper', 'final': 'ElevenLabs (paid)', 'draft': 'gTTS (free, timing only)'},
                          {'project': 'diabetes-history', 'final': 'Fasih (free, local)', 'draft': 'Fasih'}],
            'elevenlabs_account': {'used': base['character_count'], 'limit': base['character_limit'], 'read_at': base['read_at_utc'],
                                   'note': 'read once in Phase 0.5; not re-read, because reading it is itself an ElevenLabs call'},
            'spend': {'actual_units': ledger.spent('royal-oak', 'elevenlabs'), 'unit': 'characters', 'note': 'no paid run has happened'},
            'estimates': [{'what': 'Royal Oak narration as it stands', 'units': voice_data['chars_total'], 'unit': 'characters'},
                          {'what': 'If all 8 queued corrections were approved', 'units': corr, 'unit': 'characters'}],
            'lock': {'state': 'locked', 'gateway_enabled': enabled, 'approvals_recorded': len(ledger.audit_rows('approve_plan')),
                     'requires': [{'step': 'Listening checks answered for the 8 queued lines (with playback proof)', 'met': False},
                                  {'step': 'Each correction approved into the pronunciation library', 'met': False},
                                  {'step': 'Your approval of the exact cost plan (single-use, bound to its hash)', 'met': False},
                                  {'step': 'A budget set for royal-oak / ElevenLabs', 'met': ledger.remaining('royal-oak', 'elevenlabs') is not None},
                                  {'step': 'Paid generation switched on (VIDEO_DIRECTOR_PAID_ENABLED=1) on an authorised machine', 'met': enabled}]},
            'guarantee': 'Nothing on this dashboard can start a paid call: browsing, reviewing art and previewing video are read-only, and decisions only go to the event log.'}


# ---------------------------------------------------------------------------------------------------- identity
def identity(profs: dict, S: Path):
    files = {'timekeeper': sorted((S / 'audit/claude_success-story-video/video/royal-oak').glob('part*.json')),
             'diabetes-history': sorted((S / 'ep7/scenes').glob('*.js'))}
    tk_style = json.loads((S / 'audit/claude_success-story-video/video/success-story/tk-style.json').read_text(encoding='utf-8'))
    ro_style = json.loads((S / 'audit/claude_success-story-video/video/royal-oak/ro-style.json').read_text(encoding='utf-8'))
    out = {}
    for key, p in profs.items():
        others = [o for k, o in profs.items() if k != key]
        look, voice = p.get('look', {}), p.get('voice', {})
        out[key] = {'profile': p['id'], 'status': p.get('status'), 'version': p.get('version'), 'engine': p.get('engine'),
                    'palette': look.get('palette'), 'fonts': look.get('fonts'), 'logo': look.get('logo'), 'endcard': look.get('endcard'),
                    'final_voice': voice.get('final_provider'),
                    'voices': [{'name': n, 'provider': v.get('provider'), 'status': v.get('status')} for n, v in voice.get('voices', {}).items()],
                    'library_scopes': voice.get('library_scopes'), 'art_allowed': (p.get('art') or {}).get('allowed'),
                    'rules': p.get('rules'), 'contamination': {'files_checked': len(files[key]), 'hits': profiles.contamination(p, others, files[key])}}
    out['diabetes-history']['board'] = {
        'palette': [{'name': k, 'hex': v, 'source': 'episode 5–7 project (profile look)'} for k, v in profs['diabetes-history']['look']['palette'].items()],
        'type': [{'role': 'Display', 'font': 'Cairo', 'sample': 'قصة السكري', 'weight': 800, 'source': 'episode 7 code'},
                 {'role': 'Body', 'font': 'IBM Plex Sans Arabic', 'sample': 'في الدنمارك، كان طبيب يبحث عن طريقة تبقي الإنسولين تحت الجلد مدة أطول.', 'weight': 500, 'source': 'episode 7 code'},
                 {'role': 'Numbers', 'font': 'Inter', 'sample': '1936 · 1946 · 42,000', 'weight': 700, 'source': 'episode 7 code'}],
        'characters': [{'img': 'media/diabetes/board/elizabeth.jpg', 'caption': 'Elizabeth (drawn, series character kit)'},
                       {'img': 'media/diabetes/board/scientists.jpg', 'caption': 'Scientists by role; names on screen only'}],
        'image_rules': [profs['diabetes-history']['rules'].get('people'), profs['diabetes-history']['rules'].get('sources'),
                        'Forbidden sources: ' + ', '.join(profs['diabetes-history']['rules'].get('forbidden_sources', []))],
        'composition': [{'img': 'media/ep7/stills/a3.jpg', 'caption': 'Diagram scene: one chart, one chip, caption band'},
                        {'img': 'media/ep7/stills/b3.jpg', 'caption': 'Microscope scene: central circle, labelled chip'},
                        {'img': 'media/ep7/stills/d5.jpg', 'caption': 'Number scene: one figure, sourced'}],
        'motion': {'clips': ['media/ep7/clips/a4', 'media/ep7/clips/b3'],
                   'notes': ['Observed in episode 7 (not a written rule yet): layered paper drifts slowly, chips pop in, captions appear word by word.']},
        'endcard': {'img': 'media/ep7/stills/end3.jpg', 'clip': 'media/ep7/clips/end3', 'caption': 'Next-episode card (episode 7)'},
        'samples': [f'media/ep7/stills/{s}.jpg' for s in ('a1', 'b2', 'd1', 'd4')], 'logo': None,
        'logo_note': 'The series has no logo in its profile; the running header «قصة السكري» acts as its mark.'}
    tk_note = tk_style.get('_note', '')
    out['timekeeper']['board'] = {
        'palette': [{'name': 'Brand black (headline box)', 'hex': '#111111', 'source': 'timekeeper-post template'},
                    {'name': 'Brand white (headline box)', 'hex': '#FFFFFF', 'source': 'timekeeper-post template'},
                    {'name': 'Logo paper', 'hex': '#F0F0EC', 'source': 'tk-style.json note (from the logo)'}],
        'palette_film': [{'name': f'Royal Oak · {k}', 'hex': v['bg'], 'source': 'ro-style.json (film palette, not brand)'}
                         for k, v in ro_style['themes'].items() if k in ('ro-night', 'ro-paper', 'ro-steel', 'ro-blue')],
        'type': [{'role': 'Headline', 'font': 'Bahij Helvetica Neue Bold', 'sample': None, 'source': 'timekeeper-post template',
                  'missing': 'Font file not in this workspace. No sample is drawn, because a stand-in would misrepresent it.'},
                 {'role': 'Body', 'font': None, 'sample': None, 'source': None, 'missing': 'Unassigned in the brand sources.'}],
        'characters': [{'img': 'media/timekeeper/board/tk-paper.jpg', 'caption': 'Style board (M4): photo slot left empty on purpose'}],
        'image_rules': [profs['timekeeper']['rules'].get('products'), profs['timekeeper']['rules'].get('people'),
                        profs['timekeeper']['rules'].get('labels')],
        'composition': [{'img': f'media/royal-oak/animatic/frames/{s}.jpg', 'caption': f'Animatic frame {s} (storyboard text only)'}
                        for s in ('P1-03', 'P2-02', 'P3-01')],
        'motion': {'clips': ['media/timekeeper/endcard/endcard'],
                   'notes': ['Profile motion rules: people pulse 0.5 %, camera drift 3–5 %, no hold longer than 2 s, '
                             'at most 2 slides in a row.']},
        'endcard': {'img': 'media/timekeeper/endcard/still_1.jpg', 'clip': 'media/timekeeper/endcard/endcard',
                    'caption': 'Real end card, drawn here by the production renderer from tk_endcard.py'},
        'samples': [f'media/royal-oak/animatic/frames/{s}.jpg' for s in ('P1-01', 'P2-06', 'P3-02')],
        'logo': 'media/timekeeper/logo.png', 'logo_note': 'public/icon-512.png (published in the Time Keeper site)',
        'source_note': tk_note}
    a, b = out['timekeeper'], out['diabetes-history']
    out['separation'] = [
        {'check': 'Final voice providers differ', 'ok': a['final_voice'] != b['final_voice'], 'detail': f"{a['final_voice']} vs {b['final_voice']}"},
        {'check': 'Pronunciation libraries do not overlap (except global)',
         'ok': not (set(a['library_scopes']) & set(b['library_scopes'])) - {'global'}, 'detail': f"{a['library_scopes']} vs {b['library_scopes']}"},
        {'check': 'No palette colour shared', 'ok': not ({c['hex'] for c in a['board']['palette'] + a['board']['palette_film']} & {c['hex'] for c in b['board']['palette']}), 'detail': ''},
        {'check': 'Time Keeper files carry no Diabetes signatures', 'ok': not a['contamination']['hits'], 'detail': f"{a['contamination']['files_checked']} storyboards checked"},
        {'check': 'Diabetes files carry no Time Keeper signatures', 'ok': not b['contamination']['hits'], 'detail': f"{b['contamination']['files_checked']} scene files checked"},
        {'check': 'End cards differ', 'ok': a['endcard'] != b['endcard'], 'detail': f"{a['endcard']} vs {b['endcard']}"}]
    return out


# ---------------------------------------------------------------------------------------------------- build
def build(log: EventLog, S: Path, voice_data: dict, directions_data: dict, media: Path, extra_decisions: dict | None = None) -> dict:
    registry = load_registry(ROOT / 'art/techniques.yaml')
    profs = {'timekeeper': profiles.load(ROOT / 'profiles/timekeeper-luxury-doc.yaml'),
             'diabetes-history': profiles.load(ROOT / 'profiles/diabetes-history-sci.yaml')}
    decisions = {**_decisions(log), **(extra_decisions or {})}
    _LOOK_SAMPLES.clear(); _LOOK_SAMPLES.update(p.stem for p in (media / 'looks').glob('*.jpg'))
    ep7 = diabetes_ep7(log, S, decisions, registry, profs['diabetes-history'])
    ro = royal_oak(log, S, decisions, voice_data)
    checks = listening_checks(voice_data, media, decisions)
    lines = voice_lines(voice_data, ro, S, decisions)
    flagged = flags(lines, decisions)
    tasks = review_tasks(ep7, ro, checks, decisions, directions_data)
    for pk, fl in flagged.items():                      # the owner's own flags: one task per project
        if fl:
            tasks.append({'id': f'flags-{pk}', 'type': 'voice', 'project': pk, 'video': 'royal-oak' if pk == 'timekeeper' else 'ep7',
                          'scene': None, 'title': f'{len(fl)} word{"s" if len(fl) > 1 else ""} you flagged while listening',
                          'status': 'needs_decision', 'priority': 'listening', 'flags': fl,
                          'why': ', '.join(f"«{f['word']}» ({f['type_label']})" for f in fl[:6]), 'decision': None})
    for v in (ep7, ro):
        v['next_action'] = next_action(tasks, v['project'])
        v['blockers'] = ([{'what': s['label'], 'why': s['why']} for s in v['stages'] if s['status'] in ('blocked', 'failed')] +
                         [{'what': t['title'], 'why': t.get('blocked_by') or t['why']} for t in tasks
                          if t['project'] == v['project'] and t['status'] == 'blocked'])
    runs = log.runs()
    open_tasks = [t for t in tasks if t['status'] != 'done']
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'projects': {'diabetes-history': {'name': 'Diabetes History', 'videos': [ep7]},
                         'timekeeper': {'name': 'Time Keeper', 'videos': [ro]}},
            'tasks': {'running': [r for r in runs if r['state'] == 'running'], 'failed': [r for r in runs if r['state'] == 'failed'],
                      'recent': [r for r in runs if r['state'] == 'finished'][-10:]},
            'review_tasks': tasks, 'inbox_checks': checks, 'bucket_labels': BUCKET_LABEL,
            'looks': {pk: brand_looks(pk, profs[pk], registry, decisions) for pk in profs},
            'voice_lines': lines, 'flags': flagged, 'flag_types': FLAG_TYPES,
            'costs': costs(registry, voice_data, Ledger(ROOT / 'var/dashboard/ledger.sqlite'), S),
            'identity': identity(profs, S),
            'counts': {'tasks_open': len(open_tasks),
                       'by_status': dict(Counter(t['status'] for t in open_tasks)),
                       'findings_by_bucket': dict(Counter(f['bucket'] for s in ep7['scenes'] for f in s['findings'] if not f['decision']))}}
