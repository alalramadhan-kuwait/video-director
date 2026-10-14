"""Build the private, review-only copy of a Studio project for the owner's phone.

    PYTHONPATH=. python3 tools/review_copy.py VAR PROJECT OUT_DIR

Reads the project (read-only) and writes OUT_DIR/data.json plus media (720p film, scene frames from the film itself,
hook frames, concept stills, draft-voice takes). The page (tools/review_copy.html) renders it. Nothing in the output can
reach the Studio server, a provider or a key: it is a snapshot. The owner's review decisions are saved in the page's own
store and are applied to the project only when the owner asks Claude to apply them.
"""
import json, shutil, subprocess, sys
from pathlib import Path

from director.studio import api, art

VAR, PID, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
M = OUT / 'media'; M.mkdir(exist_ok=True)
V = api.view(VAR, PID)
S = api.studio(VAR)
src = lambda rel: S.path(PID, rel)


def ff(*a):
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', *map(str, a)], check=True)


def jpg(rel_or_path, name, w=540):
    p = rel_or_path if isinstance(rel_or_path, Path) else src(rel_or_path)
    ff('-i', p, '-vf', f"scale='min({w},iw)':-2", '-q:v', '5', M / name)
    return 'media/' + name


# ------------------------------------------------------------------ film
r = V['latest_render']
film = M / 'film.mp4'
ff('-i', src(r['file']), '-vf', 'scale=720:-2', '-c:v', 'libx264', '-preset', 'medium', '-crf', '26', '-profile:v', 'main',
   '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', film)
poster = 'media/poster.jpg'; ff('-ss', '0.6', '-i', film, '-frames:v', '1', '-q:v', '4', M / 'poster.jpg')
webm = M / 'film.webm'                                    # for browsers without H.264 (the iPhone uses the MP4)
ff('-i', film, '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '38', '-row-mt', '1', '-deadline', 'good', '-cpu-used', '4', '-c:a', 'libopus', '-b:a', '96k', webm)

# ------------------------------------------------------------------ scenes: frames taken from the film itself
sb = V['storyboards'][-1]
brief = V['brief']['scenes']
lines = {l['id']: l for l in V['script_versions'][sb['script_v']]}
scenes = []
for s in sb['scenes']:
    t0, d = s['start'], s['dur']
    frames = []
    for k, t in enumerate((t0 + min(1.8, d * 0.35), t0 + d * 0.7)):
        ff('-ss', f'{t:.2f}', '-i', film, '-frames:v', '1', '-vf', 'scale=360:-2', '-q:v', '5', M / f'scene-{s["id"]}-{k}.jpg')
        frames.append({'src': f'media/scene-{s["id"]}-{k}.jpg', 't': round(t, 2)})
    b = brief.get(s['id']) or brief.get('h', {})
    unreviewed = s['status']['art'] != 'approved'
    concept = V['art']['concepts'].get(s.get('concept') or '')
    versions = []
    if concept:
        for x in concept['versions']:
            versions.append({'v': x['v'], 'status': x.get('status'), 'changes': x.get('changes') or {}, 'note': x.get('note', ''),
                             'stills': [jpg(st, f'{concept["id"]}-v{x["v"]}-{i}.jpg', 360) for i, st in enumerate(x['stills'][:2])]})
    params = (b.get('concepts') or {}).get(s['technique'], {})
    chips = art.effective_changes(s['technique'], concept['versions'][-1].get('params', concept['params']) if concept else params,
                                  concept['versions'][-1].get('theme', concept['theme']) if concept else params.get('theme', b.get('theme', 'tk-bone')))
    scenes.append({'id': s['id'], 'start': t0, 'end': round(t0 + d, 2), 'dur': d, 'technique': s['technique'],
                   'banner': s.get('banner') or b.get('banner') or '', 'line': lines.get(s['id'], {}).get('text', ''),
                   'art_status': s['status']['art'], 'voice_status': s['status']['voice'], 'unreviewed': unreviewed,
                   'placeholder': 'PLACEHOLDER' in s['status']['art'],
                   'approved': {'concept': s.get('concept'), 'version': s.get('art_version')} if not unreviewed else None,
                   'frames': frames, 'versions': versions, 'concept_name': concept['name'] if concept else 'Brief default (never reviewed on its own)',
                   'chips': chips})

# ------------------------------------------------------------------ hook
H = V['hooks']
hooks = []
for o in H['options']:
    hooks.append({'id': o['id'], 'type': o.get('type', ''), 'spoken': o['spoken'], 'on_screen': o['on_screen'], 'visual': o.get('visual', ''),
                  'frames': [jpg(st, f'hook-{o["id"]}-{i}.jpg', 300) for i, st in enumerate(H['stills'].get(o['id'], []))]})
hook = {'selected': H['selected'], 'recommended': H['recommended'], 'reasons': H['reasons'], 'delivery': H['delivery'], 'options': hooks}

# ------------------------------------------------------------------ voice: every take of every line (draft voice only)
voice = []
for lid in [s['id'] for s in sb['scenes']]:
    cur = V['voice']['lines'].get(lid, {})
    takes = []
    for tid in V['voice']['by_line'].get(lid, []):
        t = V['voice']['takes'][tid]
        if t['text'] != cur.get('text'): continue                          # takes of older script text are history only
        shutil.copyfile(src(t['audio']), M / f'{tid}.mp3')
        takes.append({'id': tid, 'status': t['status'], 'seconds': t['seconds'], 'audio': f'media/{tid}.mp3', 'reason': t.get('reason', ''),
                      'words': [{'w': w['w'], 's': w['s'], 'e': w['e'], 'est': bool(w.get('est'))} for w in t['words']],
                      'heard': t.get('heard', ''), 'spoken': t['spoken'] if t['spoken'] != t['text'] else '', 'same_audio_as': t.get('same_audio_as')})
    flags = [{'word': f['word'], 'kind': f.get('kind'), 'note': f.get('note', ''), 'status': f['status'], 'respell': f.get('respell', '')}
             for f in V['voice']['flags'] if f['line'] == lid]
    voice.append({'line': lid, 'text': cur.get('text', ''), 'status': cur.get('status'), 'takes': takes, 'flags': flags})

# ------------------------------------------------------------------ art gallery (all concepts, all versions)
gallery = []
for sid, ids in V['art']['by_scene'].items():
    cs = []
    for cid in ids:
        c = V['art']['concepts'][cid]
        cs.append({'id': cid, 'name': c['name'], 'technique': c['technique'], 'support': c['support'], 'warnings': c.get('warnings', []),
                   'selected': V['art']['selected'].get(sid) == cid,
                   'versions': [{'v': x['v'], 'status': x.get('status'), 'changes': x.get('changes') or {},
                                 'stills': [jpg(st, f'g-{cid}-v{x["v"]}-{i}.jpg', 300) for i, st in enumerate(x['stills'][:1])]}
                                for x in c['versions']]})
    gallery.append({'scene': sid, 'banner': brief.get(sid, {}).get('banner', ''), 'approved': V['art']['approved'].get(sid), 'concepts': cs})

# ------------------------------------------------------------------ inbox, history, progress (snapshots)
inbox = [{'title': g['title'], 'items': [{'what': i['what'], 'wait': bool(i.get('wait'))} for i in g['items']]} for g in V['inbox_groups']]
history = [{'at': h['at'], 'actor': h['actor'], 'stage': h['stage'], 'action': h['action'], 'summary': h['summary']} for h in V['history']]
runs = [{'task': x['task'], 'stage': x['stage'], 'state': x['state'], 'units': f"{x['units_done']}/{x['units_total']}", 'elapsed_s': x['elapsed_s'],
         'started': x['started']} for x in V['runs']]
steps = [{'id': s['id'], 'name': s.get('name', s['id']), 'state': s['state']} for s in V['steps']]

data = {'project': {'id': PID, 'title': V['title'], 'idea': V['idea'], 'brand': V['brand'], 'snapshot': V['updated']},
        'film': {'src': 'media/film.mp4', 'webm': 'media/film.webm', 'poster': poster, 'seconds': r['seconds'], 'id': r['id'], 'decision': r.get('decision'),
                 'master': '1080×1920 master in the development workspace; this is a 720p review copy',
                 'size_mb': round(film.stat().st_size / 1e6, 1)},
        'storyboard': {'v': sb['v'], 'script_v': sb['script_v'], 'est_final_seconds': sb.get('est_final_seconds')},
        'scenes': scenes, 'hook': hook, 'voice': voice, 'gallery': gallery, 'inbox': inbox, 'history': history, 'runs': runs, 'steps': steps,
        'gate': {'blockers': (V['gate']['plan'] or {}).get('blockers', []), 'chars': (V['gate']['plan'] or {}).get('chars_total')},
        'chip_names': art.CHANGE_CHIPS}
(OUT / 'data.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
print(json.dumps({'scenes': len(scenes), 'unreviewed': sum(s['unreviewed'] for s in scenes), 'takes': sum(len(v['takes']) for v in voice),
                  'concepts': sum(len(g['concepts']) for g in gallery), 'media_mb': round(sum(f.stat().st_size for f in M.iterdir()) / 1e6, 1)}))

# ------------------------------------------------------------------ the page: template + embedded snapshot
page = (Path(__file__).with_name('review_copy.html')).read_text(encoding='utf-8')
(OUT / 'index.html').write_text(page.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/')), encoding='utf-8')
