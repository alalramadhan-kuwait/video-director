"""Voice review page: approved script, the exact text the voice received, the takes with waveform and word timing,
listening questions for text-check findings, take verdicts and proposed corrections. Nothing here generates audio.

What the page shows about cost is computed with the real cost plan:
  * the current request -> 'reuse' (0 characters) when an approved take exists for it;
  * a proposed correction -> a hypothetical library (the correction applied to that line only) run through the same
    plan, so the number shown is exactly what an approved paid run would bill. The hypothetical is never saved.

Findings from the text check are questions for a listener, not verdicts: «الستيل» sent as «Steel» MAY lose its
article, and only listening decides.

    python -m director.review.voice_page OUT_DIR [--mock]
"""
from __future__ import annotations
import argparse, copy, difflib, json, shutil, subprocess
from pathlib import Path
import numpy as np

from ..library import Library, Entry, bare
from ..vendor.audio_util import split_words, align, norm
from ..voice.plan import build_plan
from ..voice.takes import TakeStore, take_key

QUEUE_CODES = ('ARTICLE_DROPPED',)
COMMON_NOUNS = {'tk-steel', 'tk-quartz', 'tk-white-gold'}      # the owner's queue; brand names are shown, flagged lower


def peaks(path, n=360) -> list[int]:
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', '8000', '-f', 'f32le', '-'],
                         stdout=subprocess.PIPE, check=True).stdout
    x = np.abs(np.frombuffer(raw, dtype=np.float32))
    if not len(x):
        return [0] * n
    b = np.array_split(x, n)
    v = np.array([c.max() if len(c) else 0 for c in b])
    return [int(round(p)) for p in (v / max(v.max(), 1e-6) * 100)]


def duration(path) -> float:
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)],
                         stdout=subprocess.PIPE, check=True, text=True).stdout
    return round(float(out), 3)


def word_times(text, asr, scale=1.0):
    words = split_words(text)
    heard = [h for h in asr['words'] if norm(h['w'])]
    t = align(words, heard)
    return [{'w': w, 's': round(s * scale, 3), 'e': round(e * scale, 3)} for w, (s, e) in zip(words, t)]


def input_segments(approved: str, sent: str):
    """The exact provider input split into runs, marking the runs that differ from the approved script."""
    a, b = approved.split(' '), sent.split(' ')
    out = []
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if b1 > b0:
            out.append({'t': ' '.join(b[b0:b1]), 'changed': tag != 'equal',
                        'was': ' '.join(a[a0:a1]) if tag != 'equal' else ''})
    return out


def target_words(text, start, end):
    """Indices of the approved-script words covered by the characters [start, end) of a library match
    (by position, so a word that occurs twice in a line gets two different targets)."""
    out, pos = [], 0
    for i, w in enumerate(split_words(text)):
        a = text.index(w, pos); b = a + len(w); pos = b
        if a < end and b > start:
            out.append(i)
    return out


def what_if_keep_arabic(library: Library, line_id, text, entries, voice, store, project):
    """Cost of sending the article words of this line in Arabic (the old `_arabic` override), computed by the
    real plan on a throwaway copy of the library. Returns (provider_input, plan item)."""
    lib = Library(copy.deepcopy(library.entries), name=library.name + '+what-if')
    for eid in sorted(set(entries)):
        e = next(x for x in library.entries if x.id == eid)
        lib.entries.append(Entry(id=f'proposal-{line_id}-{eid}', scope=f'project:{project}', surface=e.surface,
                                 status='approved', article='keep', lines=[line_id],
                                 providers={voice['provider']: {'mode': 'keep_arabic'}},
                                 note='hypothetical: shown on the review page, never saved'))
    plan = build_plan(project, [{'id': line_id, 'text': text}], voice, lib, store, accept=('imported', 'approved'))
    return plan['items'][0]


def history_alternatives(history_items, sent, line_alts=0.6):
    out = []
    for it in history_items:
        r = difflib.SequenceMatcher(None, sent, it.get('text') or '').ratio()
        if line_alts < r < 1:
            out.append({'id': it['history_item_id'], 'date_unix': it['date_unix'], 'model': it['model_id'],
                        'text': it['text'], 'similarity': round(r, 2)})
    return sorted(out, key=lambda a: -a['similarity'])[:3]


def build(*, project, manifest, audio_dir, asr_dir, library, store: TakeStore, voice, out_dir,
          history=None, mock_dir=None, title='', intro=''):
    out_dir = Path(out_dir); (out_dir / 'audio').mkdir(parents=True, exist_ok=True)
    man = json.loads(Path(manifest).read_text(encoding='utf-8'))
    plan = build_plan(project, [{'id': k, 'text': v['text']} for k, v in man.items()], voice, library, store,
                      accept=('imported', 'approved'))
    items = {i['line']: i for i in plan['items']}
    lines, files = [], {}
    for lid, c in man.items():
        item = items[lid]
        src = Path(audio_dir) / f'{lid}.mp3'
        asr = json.loads((Path(asr_dir) / f'{lid}.json').read_text(encoding='utf-8'))
        rec = store.get(item['take_key'])
        takes = [{'id': item['take_key'], 'label': 'المعتمد', 'kind': 'approved',
                  'status': store.status(item['take_key']) if rec else None,
                  'audio': f'audio/{lid}.mp3', 'duration': duration(src), 'peaks': peaks(src),
                  'words': word_times(c['text'], asr)}]
        files[f'audio/{lid}.mp3'] = src
        # findings from the text check, as listening questions (one per occurrence)
        _, fs = library.prepare(c['text'], voice['provider'], line=lid, accept=('imported', 'approved'))
        matches = [m for m in library.find(c['text'], lid)]
        questions, used = [], set()
        for f in fs:
            if f.code not in QUEUE_CODES:
                continue
            for m in matches:
                if m.entry.id != f.entry or (m.start, m.end) in used:
                    continue
                used.add((m.start, m.end))
                idx = target_words(c['text'], m.start, m.end)
                questions.append({'key': f'{lid}-{m.entry.id}-{m.start}', 'entry': m.entry.id, 'written': m.text,
                                  'sent': m.entry.providers[voice['provider']].get('spoken', ''),
                                  'words': idx, 'common_noun': m.entry.id in COMMON_NOUNS})
                break
        queue = any(q['common_noun'] for q in questions)
        corr = None
        common = [q['entry'] for q in questions if q['common_noun']]
        if common:   # brand names (Royal Oak, Calibre…) are left to the owner; the correction covers the common nouns only
            alt = what_if_keep_arabic(library, lid, c['text'], common, voice, store, project)
            corr = {'keep_arabic': {'provider_input': alt['provider_input'], 'action': alt['action'],
                                    'chars': alt['chars'], 'take_key': alt['take_key']}}
        if mock_dir and queue:
            mk = make_mock(src, Path(mock_dir), lid, store, item['request'])
            takes.append({'id': mk['key'], 'label': 'تجريبي (mock)', 'kind': 'mock',
                          'status': store.status(mk['key']), 'audio': f'audio/{lid}.mock.mp3',
                          'duration': duration(mk['path']), 'peaks': peaks(mk['path']),
                          'words': word_times(c['text'], asr, scale=mk['scale']),
                          'note': 'نفس التسجيل المعتمد بسرعة أبطأ، صُنع محلياً لاختبار المقارنة فقط. ليس تسجيلاً جديداً ولا يمثّل أي تصحيح.'})
            files[f'audio/{lid}.mock.mp3'] = mk['path']
        lines.append({'id': lid, 'approved_text': c['text'], 'provider_input': item['provider_input'],
                      'input_segments': input_segments(c['text'], item['provider_input']),
                      'plan': {'action': item['action'], 'chars': item['chars'], 'take_key': item['take_key']},
                      'takes': takes, 'questions': questions, 'queue': queue, 'corrections': corr,
                      'asr_heard': ' '.join(h['w'] for h in asr['words']), 'asr_model': asr['model'],
                      'history_alternatives': history_alternatives(history or [], item['provider_input'])})
    for rel, src in files.items():
        shutil.copyfile(src, out_dir / rel)
    data = {'project': project, 'title': title, 'intro': intro, 'voice': {k: voice[k] for k in ('provider', 'model')},
            'voice_name': voice.get('name', ''), 'plan_hash': plan['hash'], 'library_version': library.version,
            'totals': plan['totals'], 'chars_total': plan['chars_total'], 'lines': lines,
            'queue': [l['id'] for l in lines if l['queue']]}
    html = (Path(__file__).parent / 'voice_template.html').read_text(encoding='utf-8')
    (out_dir / 'index.html').write_text(html.replace('__DATA__', json.dumps(data, ensure_ascii=False)), encoding='utf-8')
    (out_dir / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    return data, sorted(files)


def make_mock(src, mock_dir, lid, store: TakeStore, approved_request, tempo=0.93):
    """A clearly-labelled interface-test take: the approved audio slowed with ffmpeg. Stored as a candidate under
    provider 'mock' so it can never be mistaken for, or collide with, a real provider take."""
    mock_dir.mkdir(parents=True, exist_ok=True)
    dst = mock_dir / f'{lid}.mock.mp3'
    if not dst.exists():
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-af', f'atempo={tempo}', '-b:a', '128k', str(dst)],
                       check=True)
    req = {**approved_request, 'provider': 'mock', 'voice_id': 'mock-slowed-approved',
           'settings': {**approved_request['settings'], 'mock_tempo': tempo}}
    key = take_key(req)
    if store.get(key) is None:
        store.put(req, dst.read_bytes(), ext='mp3', status='candidate', by='voice_page.mock',
                  meta={'line': lid, 'mock': True, 'derived_from': approved_request['provider_input'][:40]})
    return {'key': key, 'path': dst, 'scale': 1 / tempo}


if __name__ == '__main__':
    import os
    from .. import importers, profiles
    from ..voice.imports import import_eleven_manifest
    from tests.fixtures import RO, RO_AUDIO, PROFILES, S
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--mock', action='store_true')
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    store = TakeStore(root / 'var/store/royal-oak')
    import_eleven_manifest(RO / 'voice-abdullah/clips.json', RO_AUDIO, store, 'royal-oak')
    lib = Library(importers.keep_arabic_overrides(RO / 'script-msa3.json') + importers.habibi_pron(RO / 'tts_habibi.py'))
    tk = profiles.load(PROFILES / 'timekeeper-luxury-doc.yaml')
    voice = {**profiles.voice_for(tk, 'abdullah', 'royal-oak'), 'name': 'Abdullah'}
    hist = json.loads((S / 'phase05/royal-oak/history_abdullah.json').read_text(encoding='utf-8'))['history']
    data, files = build(project='royal-oak', manifest=RO / 'voice-abdullah/clips.json', audio_dir=RO_AUDIO,
                        asr_dir=root / 'var/asr/royal-oak', library=lib, store=store, voice=voice, out_dir=a.out,
                        history=hist, mock_dir=(root / 'var/mock_takes/royal-oak') if a.mock else None,
                        title='Royal Oak: مراجعة الصوت')
    print(json.dumps({'lines': len(data['lines']), 'queue': data['queue'], 'totals': data['totals'],
                      'files': len(files)}, ensure_ascii=False))
