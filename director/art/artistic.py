"""Art Reviewer, part 2: the artistic pass.

The technical pass (review.py) measures things. This pass asks an independent reviewer (a model in a separate
context, or a person) to JUDGE the rendered frames against the scene metadata, the narration, the project profile and
the source evidence, across eight dimensions.

Three kinds of result are kept apart everywhere (report, page, tests):
  automated     measured by code (review.technical_pass): reproducible, no judgement involved;
  ai_judgement  a model's opinion about what it sees: a RECOMMENDATION, never proof. A factual claim it makes
                (wrong year, wrong watch, wrong person) is a lead to check against sources, not a confirmed error;
  human         the owner's decision on a finding (accepted / dismissed / needs_source / fixed).

Nothing in this module edits artwork. Findings are data; decisions are appended to a log; the person fixes the art.
"""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path

DIMENSIONS = {
    'composition':      'Composition and visual hierarchy',
    'accuracy':         'Historical and technical accuracy',
    'narration_match':  'Does the image match the narration?',
    'identity':         'Correct watches, products and people',
    'arabic_text':      'Readability of Arabic text',
    'style':            'Consistency with the approved project style',
    'light_colour':     'Lighting, colours and character proportions',
    'motion_story':     'Motion and storytelling quality',
}
FACTUAL = {'accuracy', 'identity', 'narration_match'}          # claims about the world, not about taste
SEVERITIES = ('critical', 'major', 'minor', 'info')
SOURCES = ('automated', 'ai_judgement', 'human')
STATUSES = ('proposed', 'accepted', 'dismissed', 'needs_source', 'fixed')
CONFIDENCE = ('low', 'medium', 'high')
EVIDENCE_KINDS = ('still', 'strip', 'contact', 'metadata', 'narration', 'fact', 'profile', 'measurement')


def tc(t: float) -> str:
    m, s = divmod(max(0.0, float(t)), 60)
    return f'{int(m):02d}:{s:04.1f}'


# ------------------------------------------------------------------------------------------------ request
def build_request(pack: dict, scenes: dict, profile: dict, facts: list[dict], dimensions=tuple(DIMENSIONS),
                  include_technical=None) -> dict:
    """What the independent reviewer receives. `scenes` maps scene id -> {narration, plan, on_screen_text, people,
    products}. Technical findings are NOT included by default, so the artistic judgement is not anchored by them."""
    items = []
    for s in pack['scenes']:
        meta = scenes.get(s['id'], {})
        items.append({'scene': s['id'], 'start': s['start'], 'end': s['end'], 'timecode': f"{tc(s['start'])}–{tc(s['end'])}",
                      'stills': s['stills'], 'strip': s['strip'], **{k: meta.get(k) for k in
                      ('narration', 'plan', 'on_screen_text', 'people', 'products') if meta.get(k)}})
    req = {'kind': 'artistic_review_request', 'video': pack.get('video'), 'contact': pack.get('contact'),
           'profile': {'id': profile['id'], 'status': profile.get('status'), 'palette': profile.get('palette'),
                       'fonts': profile.get('fonts'), 'motifs': profile.get('motifs'), 'avoid': profile.get('avoid')},
           'facts': facts, 'dimensions': {d: DIMENSIONS[d] for d in dimensions}, 'scenes': items,
           'rules': RULES, 'finding_schema': FINDING_SCHEMA}
    if include_technical is not None:
        req['technical'] = include_technical
    req['hash'] = hashlib.sha256(json.dumps(req, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return req


RULES = [
    'Look at the stills and strips themselves. Judge only what is visible or what the metadata/facts say.',
    'Every finding cites evidence by its file path (still/strip/contact) and, for factual claims, the fact id it relies on.',
    'A factual claim with no fact to rely on is still allowed, but say "no source in facts" and set confidence low.',
    'You are recommending, not deciding: do not call a finding confirmed. Severity: critical (wrong fact or identity on screen, '
    'unreadable key text), major (clearly hurts the scene), minor (polish), info (observation).',
    'Suggest a correction a designer could act on. Do not rewrite the art yourself.',
    'If a scene has no problem in a dimension, say nothing for it. No praise findings.',
]
FINDING_SCHEMA = {'scene': 'scene id', 't': 'seconds (inside the scene)', 'dimension': list(DIMENSIONS),
                  'problem': 'one or two sentences', 'severity': list(SEVERITIES), 'confidence': list(CONFIDENCE),
                  'evidence': [{'kind': list(EVIDENCE_KINDS), 'ref': 'file path or fact id', 'note': 'what to look at'}],
                  'suggestion': 'what to change', 'claim': 'factual | aesthetic | technical'}


# ------------------------------------------------------------------------------------------------ validation
def accept_ai_findings(raw: list[dict], request: dict, reviewer: dict) -> tuple[list[dict], list[dict]]:
    """Turn a reviewer's raw output into findings. Whatever the reviewer wrote, the result is labelled
    ai_judgement, status 'proposed', requires_human True. Returns (kept, discarded-with-reason)."""
    scenes = {s['scene']: s for s in request['scenes']}
    files = {request.get('contact')} | {p for s in request['scenes'] for p in [*s['stills'].values(), s['strip']]}
    fact_ids = {f['id'] for f in request.get('facts', [])}
    kept, dropped = [], []
    for n, r in enumerate(raw):
        why = None
        sc = scenes.get(r.get('scene'))
        dim = r.get('dimension')
        ev = [e for e in (r.get('evidence') or []) if isinstance(e, dict)]
        visual = [e for e in ev if e.get('ref') in files]
        cited = [e for e in ev if e.get('kind') == 'fact' and e.get('ref') in fact_ids]
        if sc is None: why = f"unknown scene {r.get('scene')!r}"
        elif dim not in DIMENSIONS: why = f'unknown dimension {dim!r}'
        elif not (r.get('problem') or '').strip(): why = 'no problem described'
        elif not visual and dim not in ('narration_match',) and not cited: why = 'no evidence in the packet was cited'
        if why:
            dropped.append({'raw': r, 'reason': why}); continue
        t = r.get('t')
        t = sc['start'] if not isinstance(t, (int, float)) else min(max(float(t), sc['start']), sc['end'])
        sev = r.get('severity') if r.get('severity') in SEVERITIES else 'minor'
        conf = r.get('confidence') if r.get('confidence') in CONFIDENCE else 'low'
        claim = r.get('claim') if r.get('claim') in ('factual', 'aesthetic', 'technical') else (
            'factual' if dim in FACTUAL else 'aesthetic')
        notes = []
        if claim == 'factual' and not cited:
            notes.append('factual claim without a cited fact: check the source before acting')
            conf = 'low' if conf == 'high' else conf
            if sev == 'critical': sev = 'major'; notes.append('severity capped: an uncited factual claim cannot be critical')
        body = {'scene': sc['scene'], 't': round(t, 2), 'timecode': tc(t), 'scene_timecode': sc['timecode'],
                'dimension': dim, 'dimension_label': DIMENSIONS[dim], 'problem': r['problem'].strip(),
                'severity': sev, 'confidence': conf, 'claim': claim, 'evidence': ev,
                'suggestion': (r.get('suggestion') or '').strip(), 'source': 'ai_judgement', 'status': 'proposed',
                'requires_human': True, 'reviewer': reviewer, 'notes': notes}
        body['id'] = 'f_' + hashlib.sha256(json.dumps([body['scene'], dim, body['problem']], ensure_ascii=False).encode()).hexdigest()[:10]
        kept.append(body)
    return kept, dropped


def from_technical(tech: list[dict], pack: dict) -> list[dict]:
    """review.technical_pass findings in the same shape, labelled automated."""
    out = []
    for f in tech:
        t = f.get('t') or 0.0
        out.append({'id': 'a_' + hashlib.sha256(json.dumps([f['code'], f.get('scene'), t]).encode()).hexdigest()[:10],
                    'scene': f.get('scene'), 't': t, 'timecode': tc(t), 'dimension': 'technical', 'dimension_label': f['code'],
                    'problem': f['detail'], 'severity': f['severity'], 'confidence': 'high', 'claim': 'technical',
                    'evidence': [{'kind': 'measurement', 'ref': f['code'], 'note': json.dumps(f.get('evidence'), ensure_ascii=False)}],
                    'suggestion': f.get('suggestion', ''), 'source': 'automated', 'status': 'proposed',
                    'requires_human': f['severity'] in ('critical', 'major') and f['code'] not in ('WRONG_SIZE', 'TOO_LONG', 'LOUDNESS', 'TRUE_PEAK'),
                    'reviewer': {'kind': 'code', 'name': 'review.technical_pass'}, 'notes': []})
    return out


def report(technical: list[dict], ai: list[dict], dropped: list[dict], request: dict) -> dict:
    order = {s: i for i, s in enumerate(SEVERITIES)}
    key = lambda f: (order[f['severity']], f['t'] or 0)
    return {'request': request['hash'], 'video': request.get('video'),
            'automated': sorted(technical, key=key), 'ai_judgement': sorted(ai, key=key), 'discarded_ai': dropped,
            'needs_human': [f['id'] for f in sorted(technical + ai, key=key) if f['requires_human']],
            'counts': {'automated': len(technical), 'ai_judgement': len(ai), 'discarded_ai': len(dropped),
                       'needs_human': sum(f['requires_human'] for f in technical + ai)},
            'created': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}


# ------------------------------------------------------------------------------------------------ decisions
def decide(log_path, finding_id: str, status: str, by: str, note: str = '') -> dict:
    """Owner decision on one finding, appended to a log. It never touches artwork or the finding itself."""
    if status not in STATUSES or status == 'proposed':
        raise ValueError(f'status must be one of {STATUSES[1:]}')
    row = {'finding': finding_id, 'status': status, 'by': by, 'note': note,
           'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    return row


def current_status(log_path, finding_id: str) -> str:
    p = Path(log_path)
    if not p.exists():
        return 'proposed'
    rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    rows = [r for r in rows if r['finding'] == finding_id]
    return rows[-1]['status'] if rows else 'proposed'


# ------------------------------------------------------------------------------------------------ blind test scoring
def score(findings: list[dict], truth: dict) -> dict:
    """truth: item id -> {'defect': bool, 'dimensions': [...acceptable dimensions...], 'what': str}.
    A defect counts as caught when any finding on that item names one of its acceptable dimensions."""
    by_item = {}
    for f in findings:
        by_item.setdefault(f['scene'], []).append(f)
    rows, tp, fn, fp_items, clean = [], 0, 0, 0, 0
    for item, t in truth.items():
        fs = by_item.get(item, [])
        if t['defect']:
            hit = [f for f in fs if f['dimension'] in t['dimensions']]
            tp += bool(hit); fn += not hit
            rows.append({'item': item, 'defect': t['what'], 'caught': bool(hit), 'by': [f['id'] for f in hit],
                         'other_findings': len(fs) - len(hit)})
        else:
            clean += 1
            serious = [f for f in fs if f['severity'] in ('critical', 'major')]
            fp_items += bool(serious)
            rows.append({'item': item, 'defect': None, 'caught': None, 'serious_findings_on_clean': len(serious),
                         'other_findings': len(fs) - len(serious)})
    return {'defects': tp + fn, 'caught': tp, 'missed': fn, 'recall': round(tp / max(1, tp + fn), 2),
            'clean_items': clean, 'clean_items_with_major_or_critical': fp_items, 'rows': rows}
