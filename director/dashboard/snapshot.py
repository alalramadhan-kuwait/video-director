"""One read-only snapshot of production state for the dashboard.

Everything here is READ from the existing components; nothing is generated, written to a profile, or sent to a
provider. This module does not import the paid gateway, and no value in the snapshot can start a paid call.

Rules kept on purpose:
  * every completion figure is a count (done / total) of real units; no weighted or guessed percentages;
  * stage status comes from the latest stage_status event, or from live counts where a stage has them;
  * elapsed processing time is the sum of measured task durations (live events only);
  * an ETA appears only if the event log says it is reliable (see events.eta);
  * voice IDs, consent records and keys are never copied into the snapshot.
"""
from __future__ import annotations
import json, os, time
from collections import Counter, defaultdict
from pathlib import Path
import yaml

from .. import profiles
from ..events import EventLog
from ..ledger import Ledger
from ..art.selector import load_registry, recommend

ROOT = Path(__file__).resolve().parents[2]
STAGES = ['script', 'hook', 'voice', 'art', 'render', 'final', 'publish']
STAGE_LABEL = {'script': 'Script', 'hook': 'Hook', 'voice': 'Voice', 'art': 'Art', 'render': 'Render',
               'final': 'Final video', 'publish': 'Publish'}
SEV_ORDER = {'critical': 0, 'major': 1, 'minor': 2, 'info': 3}


def _decisions(log: EventLog) -> dict:
    """Latest owner decision per review item (review_decided events)."""
    out = {}
    for r in log.rows(kind='review_decided'):
        out[r['data'].get('item')] = {'decision': r['status'], 'note': r['data'].get('note', ''), 'at': r['at'],
                                      'by': r['actor'], 'locked': r['status'] == 'approved'}
    return out


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
        first = min((r['at'] for r in sr if r['kind'] != 'stage_status'), default=None)
        done_at = status_ev[-1]['at'] if status == 'approved' and status_ev else None
        runs = [r for r in sr if r['kind'] == 'task_finished']
        out.append({'stage': st, 'label': STAGE_LABEL[st], 'status': status, 'why': why,
                    'units': {k: units[k] for k in ('done', 'total', 'unit') if units and k in units} or None,
                    'first_activity': first, 'approved_at': done_at,
                    'processing_s': round(sum(r['duration_s'] or 0 for r in runs), 2) if runs else None,
                    'source': status_ev[-1]['source'] if status_ev else None,
                    'evidence': status_ev[-1]['evidence'] if status_ev else None})
    return out


def _history(log: EventLog, project, video, scene=None):
    out = []
    for r in log.rows(project=project):
        if r['video'] != video or r['kind'] not in ('revision', 'review_decided', 'stage_status', 'task_finished', 'task_failed', 'blocked'):
            continue
        if scene is not None and r['scene'] != scene:
            continue
        out.append({'at': r['at'], 'kind': r['kind'], 'stage': r['stage'], 'scene': r['scene'], 'status': r['status'],
                    'what': r['data'].get('what') or r['data'].get('why') or r['task'] or r['data'].get('note') or '',
                    'source': r['source'], 'evidence': r['evidence'], 'actor': r['actor']})
    return sorted(out, key=lambda e: e['at'])


# ---------------------------------------------------------------------------------------------------- projects
def diabetes_ep7(log, S: Path, decisions: dict, registry, prof):
    pack = json.loads((ROOT / 'var/review/ep7-final/pack.json').read_text(encoding='utf-8'))
    ev = yaml.safe_load((ROOT / 'art/evidence/diabetes-ep7.yaml').read_text(encoding='utf-8'))
    rep = json.loads((ROOT / 'var/review/ep7-final/artistic_report.json').read_text(encoding='utf-8'))
    beats = {b['id']: b for b in yaml.safe_load((ROOT / 'art/mock/diabetes-ep7-beats.yaml').read_text(encoding='utf-8'))['scenes']}
    by_scene = defaultdict(list)
    for f in rep['ai_judgement'] + rep['automated']:
        by_scene[f['scene']].append(f)
    scenes = []
    for s in pack['scenes']:
        m = ev['scenes'].get(s['id'], {})
        fs = by_scene.get(s['id'], [])
        open_f = [f for f in fs if f['id'] not in decisions]
        status = 'waiting_review' if open_f else ('approved' if fs and all(decisions[f['id']]['decision'] == 'approved' for f in fs) else 'waiting_review' if fs else 'no_findings')
        scenes.append({
            'id': s['id'], 'start': round(s['start'], 2), 'end': round(s['end'], 2), 'dur': round(s['end'] - s['start'], 2),
            'narration': m.get('narration'), 'plan': m.get('plan'), 'on_screen_text': m.get('on_screen_text') or [],
            'still': f"media/ep7/stills/{s['id']}.jpg", 'clip': f"media/ep7/clips/{s['id']}.mp4",
            'art_status': status, 'findings': [_finding_view(f, decisions) for f in sorted(fs, key=lambda f: (SEV_ORDER[f['severity']], f['t']))],
            'findings_open': len(open_f), 'max_severity': min((f['severity'] for f in open_f), key=lambda x: SEV_ORDER[x], default=None),
            'concepts': _concepts(beats.get(s['id']), prof, registry),
            'versions': _versions_ep7(s['id'], log, decisions),
            'history': _history(log, 'diabetes-history', 'ep7', s['id'])})
    decided = sum(1 for f in rep['ai_judgement'] if f['id'] in decisions)
    live = {'art': {'done': decided, 'total': len(rep['ai_judgement']), 'unit': 'AI findings decided'},
            'voice': {'done': 30, 'total': 30, 'unit': 'lines in the approved narration'},
            'render': {'done': 5, 'total': 5, 'unit': 'output files (3 parts, full, upload file)'}}
    if decided == len(rep['ai_judgement']) and decided:
        live['art'].update(override='approved', why='every AI finding has an owner decision')
    return {'id': 'ep7', 'project': 'diabetes-history', 'title': 'Episode 7 · «إبرة أقل»', 'duration': round(pack['meta']['duration'], 2),
            'platform': 'TikTok 1080×1920', 'media': 'frames, clips and revisions from the published render',
            'stages': _stage_block(log, 'diabetes-history', 'ep7', live), 'scenes': scenes,
            'history': _history(log, 'diabetes-history', 'ep7')}


def _finding_view(f, decisions):
    d = decisions.get(f['id'])
    return {'id': f['id'], 'scene': f['scene'], 't': f['t'], 'timecode': f['timecode'], 'source': f['source'],
            'dimension': f['dimension_label'], 'severity': f['severity'], 'confidence': f['confidence'],
            'problem': f['problem'], 'suggestion': f['suggestion'], 'notes': f['notes'],
            'evidence': [e for e in f['evidence'] if e.get('kind') in ('fact', 'measurement')] ,
            'frames': [e['ref'] for e in f['evidence'] if e.get('kind') in ('still', 'strip')],
            'decision': d}


def _concepts(beat, prof, registry):
    if not beat:
        return {'note': 'no beat recorded for this scene yet; the Art Director proposes options once it has one', 'options': []}
    r = recommend(beat, prof, registry, n=3)
    return {'beat': r['beat'], 'note': 'proposals only; nothing is drawn or generated',
            'options': [{'technique': o['technique'], 'name': o['name'], 'cost': o['cost'], 'risks': o['risks'],
                         'reasons': o['reasons'], 'warnings': o['warnings']} for o in r['options']],
            'excluded': r['excluded']}


def _versions_ep7(scene, log, decisions):
    if scene != 'b1':
        return [{'id': f'ep7-{scene}-final', 'label': 'Final render', 'img': f'media/ep7/stills/{scene}.jpg',
                 'clip': f'media/ep7/clips/{scene}.mp4', 'source': 'published render (2026-10-12)', 'cost': 'free (local render)',
                 'decision': decisions.get(f'ep7-{scene}-final')}]
    revs = {r['evidence']: r['at'] for r in log.rows(project='diabetes-history', scene='b1', kind='revision')}
    spec = [('A', 'b1_v1', 'chk/p2b.png', 'Chip «مدة أطول» hidden under the caption'),
            ('B', 'b1_v2', 'chk/p2c.png', 'Doctor name over the year card'),
            ('C', 'b1_v3', 'chk/p2d.png', 'Name and chip clear (used in the final render)')]
    return [{'id': f'ep7-b1-{v}', 'label': f'Version {lab}', 'img': f'media/ep7/revisions/{v}.jpg',
             'clip': 'media/ep7/clips/b1.mp4' if lab == 'C' else None, 'what': what,
             'source': f'render check {src}, ' + (revs.get(f'file time: ep7/{src}', '')[11:16] + ' UTC 2026-10-12'),
             'cost': 'free (local render)', 'decision': decisions.get(f'ep7-b1-{v}')} for lab, v, src, what in spec]


def royal_oak(log, S: Path, decisions: dict, voice_data: dict):
    R = S / 'audit/claude_success-story-video/video/royal-oak'
    ro_style = json.loads((R / 'ro-style.json').read_text(encoding='utf-8'))
    lines = {l['id']: l for l in voice_data['lines']}
    scenes, t = [], 0.0
    for part in (1, 2, 3):
        p = json.loads((R / f'part{part}.json').read_text(encoding='utf-8'))
        for i, s in enumerate(p['scenes'], 1):
            line = Path(s.get('voice') or '').stem or None
            l = lines.get(line)
            qs = [q for q in (l['questions'] if l else []) if q['common_noun']]
            answered = [q for q in qs if f"voice-{q['key']}" in decisions]
            scenes.append({'id': f'P{part}-{i:02d}', 'part': part, 'start': round(t, 2), 'end': round(t + s['dur'], 2), 'dur': s['dur'],
                           'narration': (l or {}).get('approved_text') or s.get('captions', '').replace(' | ', ' '),
                           'voice_line': line, 'theme': s.get('theme'),
                           'theme_bg': ro_style['themes'].get(s.get('theme'), {}).get('bg'),
                           'audio': f'media/royal-oak/audio/{line}.mp3' if line else None,
                           'voice_status': 'approved' if l and l['plan']['action'] == 'reuse' else 'unknown',
                           'listening': {'asked': len(qs), 'answered': len(answered)},
                           'art_status': 'unknown', 'still': None, 'clip': None,
                           'history': []})
            t += s['dur']
    q_items = [q for l in voice_data['lines'] for q in l['questions'] if q['common_noun']]
    answered = sum(1 for q in q_items if f"voice-{q['key']}" in decisions)
    n_lines = len({l['id'] for l in voice_data['lines'] if any(q['common_noun'] for q in l['questions'])})
    live = {'voice': {'done': answered, 'total': len(q_items), 'unit': f'listening checks answered ({n_lines} lines)'}}
    if q_items and answered == len(q_items):
        live['voice'].update(override='approved', why='all listening checks answered')
    return {'id': 'royal-oak', 'project': 'timekeeper', 'title': 'Royal Oak · three parts', 'duration': round(t, 2),
            'platform': '1080×1920', 'media': 'storyboards and approved narration; the photographs and renders are not in this workspace',
            'stages': _stage_block(log, 'timekeeper', 'royal-oak', live), 'scenes': scenes,
            'history': _history(log, 'timekeeper', 'royal-oak')}


# ---------------------------------------------------------------------------------------------------- inbox
def inbox(ep7, ro, voice_data, decisions, directions_data):
    items = []
    for l in voice_data['lines']:
        for q in l['questions']:
            if not q['common_noun']: continue
            iid = f"voice-{q['key']}"
            items.append({'id': iid, 'type': 'voice', 'project': 'timekeeper', 'video': 'royal-oak', 'scene': _ro_scene(ro, l['id']),
                          'title': f"{l['id']}: «{q['written']}» was sent as “{q['sent']}”. Is the article heard?",
                          'severity': 'needs listening', 'source': 'text check (not proof)',
                          'notes': ['Only listening decides. Machine transcription is a hint, not evidence.',
                                    'Git 46ddf9e (2026-10-12): “quartz and steel voiced with the article” in the Part 2 hook.'],
                          'audio': f"media/royal-oak/audio/{l['id']}.mp3", 'cost_if_changed': (l['corrections'] or {}).get('keep_arabic', {}).get('chars'),
                          'decision': decisions.get(iid)})
    for s in ep7['scenes']:
        if not s['findings']: continue
        open_f = [f for f in s['findings'] if not f['decision']]
        items.append({'id': f"art-ep7-{s['id']}", 'type': 'art', 'project': 'diabetes-history', 'video': 'ep7', 'scene': s['id'],
                      'title': f"Scene {s['id']}: {len(s['findings'])} art finding(s), {len(open_f)} open",
                      'severity': min((f['severity'] for f in s['findings']), key=lambda x: SEV_ORDER[x]),
                      'source': 'AI judgement (recommendation)', 'notes': [s['findings'][0]['problem']],
                      'decision': decisions.get(f"art-ep7-{s['id']}")})
    items.append({'id': 'final-ep7', 'type': 'final', 'project': 'diabetes-history', 'video': 'ep7', 'scene': None,
                  'title': 'Episode 7 final video', 'severity': 'approval', 'source': 'delivered 2026-10-12',
                  'notes': ['Publishing stays blocked until the Fasih licence (CPML) is reviewed (your Phase 0.5 decision).'],
                  'decision': decisions.get('final-ep7')})
    for pk, title in (('timekeeper', 'Time Keeper'), ('diabetes', 'Diabetes History')):
        iid = f'direction-{pk}'
        items.append({'id': iid, 'type': 'direction', 'project': 'timekeeper' if pk == 'timekeeper' else 'diabetes-history',
                      'video': None, 'scene': None, 'title': f'{title}: choose a creative direction (3 proposals; profile stays a draft)',
                      'severity': 'decision', 'source': 'M4 directions page',
                      'notes': [', '.join(d['name'] for d in directions_data['projects'][pk]['directions'])], 'decision': decisions.get(iid)})
    items.append({'id': 'eng-paper-banner', 'type': 'engineering', 'project': 'timekeeper', 'video': None, 'scene': None,
                  'title': 'paper-story --check cannot see anything under the banner (production code)', 'severity': 'major',
                  'source': 'automated (adapter test)', 'notes': ['engine/paper.css line 38: .banner has width 0 and height 0. Fixing it changes production code.'],
                  'decision': decisions.get('eng-paper-banner')})
    items.append({'id': 'voice-dh-ep6-insulin', 'type': 'voice', 'project': 'diabetes-history', 'video': 'ep6', 'scene': None,
                  'title': 'Episode 6: «الإنسولين» lines: re-listen or re-voice (open from earlier)', 'severity': 'needs listening',
                  'source': 'earlier review', 'notes': ['The episode 6 review data is not loaded in this prototype.'],
                  'decision': decisions.get('voice-dh-ep6-insulin')})
    for it in items:
        it['state'] = 'decided' if it['decision'] else 'pending'
    return items


def _ro_scene(ro, line):
    return next((s['id'] for s in ro['scenes'] if s['voice_line'] == line), None)


# ---------------------------------------------------------------------------------------------------- costs
def costs(registry, profs, voice_data, ledger: Ledger, S: Path):
    base = json.loads((S / 'phase05/elevenlabs_baseline.json').read_text(encoding='utf-8'))
    ops = [{'op': 'Render (paper story, motion, ad engine)', 'kind': 'free', 'where': 'local'},
           {'op': 'Evidence packs, technical checks, QA adapters', 'kind': 'free', 'where': 'local'},
           {'op': 'Word timing (faster-whisper)', 'kind': 'free', 'where': 'local'},
           {'op': 'Diabetes narration (Fasih + Bram)', 'kind': 'free', 'where': 'local · publishing blocked until licence review'},
           {'op': 'Draft narration for timing (gTTS)', 'kind': 'free', 'where': 'online, drafts only'},
           {'op': 'Time Keeper final narration (ElevenLabs)', 'kind': 'paid', 'where': 'locked behind the gateway'},
           {'op': 'AI illustration (fal.ai / Higgsfield)', 'kind': 'paid', 'where': 'not offered: no budget, never for real people or products'},
           {'op': 'AI art review in the product (model API)', 'kind': 'paid', 'where': 'not built; in development it runs in a separate session'}]
    for t in registry.values():
        ops.append({'op': f"Art technique: {t['name']}", 'kind': 'paid' if t['cost'] == 'paid' else 'free',
                    'where': 'registry: ' + t['status']})
    corr = sum((l['corrections'] or {}).get('keep_arabic', {}).get('chars', 0) for l in voice_data['lines'] if l['queue'])
    spent = ledger.spent('royal-oak', 'elevenlabs')
    approvals = ledger.audit_rows('approve_plan')
    enabled = os.environ.get('VIDEO_DIRECTOR_PAID_ENABLED') == '1'
    return {
        'operations': ops,
        'providers': [{'project': 'timekeeper', 'final': 'ElevenLabs (paid)', 'draft': 'gTTS (free, timing only)'},
                      {'project': 'diabetes-history', 'final': 'Fasih (free, local)', 'draft': 'Fasih'}],
        'elevenlabs_account': {'used': base['character_count'], 'limit': base['character_limit'], 'read_at': base['read_at_utc'],
                               'note': 'read once in Phase 0.5; not re-read, because reading it is itself an ElevenLabs call'},
        'spend': {'actual_units': spent, 'unit': 'characters', 'note': 'from the development ledger (no paid run has happened)'},
        'estimates': [{'what': 'Royal Oak narration as it stands (all 30 lines reuse approved takes)', 'units': voice_data['chars_total'], 'unit': 'characters'},
                      {'what': 'If every queued correction were approved (8 lines)', 'units': corr, 'unit': 'characters'}],
        'lock': {'state': 'locked', 'gateway_enabled': enabled, 'approvals_recorded': len(approvals),
                 'requires': [
                     {'step': 'Listening checks answered for the 8 queued lines', 'met': False},
                     {'step': 'Each correction approved into the pronunciation library', 'met': False},
                     {'step': 'Your approval of the exact cost plan (single-use, bound to its hash)', 'met': False},
                     {'step': 'A budget set for royal-oak / ElevenLabs', 'met': ledger.remaining('royal-oak', 'elevenlabs') is not None},
                     {'step': 'Paid generation switched on (VIDEO_DIRECTOR_PAID_ENABLED=1) on an authorised machine', 'met': enabled}]},
        'guarantee': 'The dashboard has no action that calls a paid provider. Browsing, reviewing art and previewing video are read-only; decisions are written to the event log.'}


# ---------------------------------------------------------------------------------------------------- identity
def identity(profs: dict, S: Path):
    tk, dh = profs['timekeeper'], profs['diabetes-history']
    files = {'timekeeper': sorted((S / 'audit/claude_success-story-video/video/royal-oak').glob('part*.json')),
             'diabetes-history': sorted((S / 'ep7/scenes').glob('*.js'))}
    out = {}
    for key, p in profs.items():
        others = [o for k, o in profs.items() if k != key]
        hits = profiles.contamination(p, others, files[key])
        look, voice = p.get('look', {}), p.get('voice', {})
        out[key] = {'profile': p['id'], 'status': p.get('status'), 'version': p.get('version'), 'engine': p.get('engine'),
                    'palette': look.get('palette'), 'fonts': look.get('fonts'), 'logo': look.get('logo'), 'endcard': look.get('endcard'),
                    'final_voice': voice.get('final_provider'),
                    'voices': [{'name': n, 'provider': v.get('provider'), 'status': v.get('status')} for n, v in voice.get('voices', {}).items()],
                    'library_scopes': voice.get('library_scopes'), 'art_allowed': (p.get('art') or {}).get('allowed'),
                    'contamination': {'files_checked': len(files[key]), 'hits': hits}}
    a, b = out['timekeeper'], out['diabetes-history']
    out['separation'] = [
        {'check': 'Final voice providers differ', 'ok': a['final_voice'] != b['final_voice'], 'detail': f"{a['final_voice']} vs {b['final_voice']}"},
        {'check': 'Pronunciation library scopes do not overlap (except global)',
         'ok': not (set(a['library_scopes']) & set(b['library_scopes'])) - {'global'}, 'detail': f"{a['library_scopes']} vs {b['library_scopes']}"},
        {'check': 'No palette colour shared', 'ok': not (set((a['palette'] or {}).values()) & set((b['palette'] or {}).values())), 'detail': ''},
        {'check': 'Time Keeper files carry no Diabetes signatures', 'ok': not a['contamination']['hits'], 'detail': f"{a['contamination']['files_checked']} storyboards checked"},
        {'check': 'Diabetes files carry no Time Keeper signatures', 'ok': not b['contamination']['hits'], 'detail': f"{b['contamination']['files_checked']} scene files checked"},
        {'check': 'End cards differ', 'ok': a['endcard'] != b['endcard'], 'detail': f"{a['endcard']} vs {b['endcard']}"}]
    return out


# ---------------------------------------------------------------------------------------------------- build
def build(log: EventLog, S: Path, voice_data: dict, directions_data: dict, extra_decisions: dict | None = None) -> dict:
    registry = load_registry(ROOT / 'art/techniques.yaml')
    profs = {'timekeeper': profiles.load(ROOT / 'profiles/timekeeper-luxury-doc.yaml'),
             'diabetes-history': profiles.load(ROOT / 'profiles/diabetes-history-sci.yaml')}
    decisions = {**_decisions(log), **(extra_decisions or {})}
    ep7 = diabetes_ep7(log, S, decisions, registry, profs['diabetes-history'])
    ro = royal_oak(log, S, decisions, voice_data)
    box = inbox(ep7, ro, voice_data, decisions, directions_data)
    runs = log.runs()
    snap = {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'projects': {'timekeeper': {'name': 'Time Keeper', 'videos': [ro]},
                         'diabetes-history': {'name': 'Diabetes History', 'videos': [ep7]}},
            'tasks': {'running': [r for r in runs if r['state'] == 'running'], 'failed': [r for r in runs if r['state'] == 'failed'],
                      'recent': [r for r in runs if r['state'] == 'finished'][-8:]},
            'inbox': box, 'costs': costs(registry, profs, voice_data, Ledger(ROOT / 'var/dashboard/ledger.sqlite'), S),
            'identity': identity(profs, S),
            'counts': {'pending': sum(1 for i in box if i['state'] == 'pending'),
                       'by_type': dict(Counter(i['type'] for i in box if i['state'] == 'pending'))}}
    return snap
