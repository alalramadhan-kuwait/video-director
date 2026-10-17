"""Draft-voice tools for Gate 3 (free, local; never the final voice).

  qa()      checks every current take: lines with no take, speaking pace, level and clipping, and words the
            transcription could not place (UNCERTAIN: a person has to listen; the machine does not judge pronunciation).
  mix()     one play-all narration (the current take of every line, in order, short gaps) with each line's place in it,
            so the owner can listen once and the page knows which lines were heard. Rebuilt whenever a take changes.
  adjust()  speed and pauses for one line, processed here with ffmpeg (atempo + silence). The result is a NEW take
            labelled as locally processed draft audio; the take it came from is kept unchanged. Word times move with it.
"""
from __future__ import annotations
import hashlib, json

import numpy as np

from ..studio import voice as V

GAP = 0.35
LABEL_ADJ = 'DRAFT VOICE (gTTS, free) — speed/pauses processed locally (ffmpeg, free) — not the final voice'


def spoken_now(st) -> dict:
    """line -> what the draft voice should say for it under the pronunciation dictionary as it stands now."""
    lib = V.library_for(None, st['id'], st)
    return {lid: lib.prepare(x['text'], V.PROVIDER, line=lid)[0] for lid, x in (st['voice'].get('lines') or {}).items()}


def effective_takes(st) -> dict:
    """line -> the take to review now. Only takes made for the line's current text AND its current spelling count (a
    correction that was withdrawn no longer has a say). Among them, a newer undecided take (a re-take, a speed change)
    replaces the approved one in the play-all, so the owner hears the replacement; until it is approved the approved
    take stays in use. No take for the current spelling yet: the line's current take, until the new one is recorded."""
    vl = st['voice'].get('lines') or {}
    tk = st['voice']['takes']
    sp = spoken_now(st)
    out = {}
    for lid, x in vl.items():
        ok = [i for i in st['voice']['by_line'].get(lid, []) if tk[i]['text'] == x['text'] and tk[i].get('spoken', x['text']) == sp[lid]]
        if not ok:
            out[lid] = x['take']
            continue
        base = next((i for i in reversed(ok) if tk[i]['status'] == 'approved'), None)
        if base:
            pend = [i for i in ok[ok.index(base) + 1:] if tk[i]['status'] == 'candidate']
            out[lid] = pend[-1] if pend else base
        else:
            out[lid] = ok[-1]
    return out


def _db(x):
    return round(20 * float(np.log10(max(x, 1e-9))), 1)


def qa(studio, pid, st) -> dict:
    vl = st['voice'].get('lines') or {}
    eff = effective_takes(st)
    flags, by_take = [], {}
    for lid, x in vl.items():
        x = {**x, 'take': eff.get(lid)}
        if not x['take']:
            flags.append({'id': f'q-{lid}-missing', 'line': lid, 'take': None, 'code': 'MISSING', 'severity': 'major', 'status': 'open',
                          'detail': 'no draft take for this line', 'detail_ar': 'لا يوجد تسجيل لهذا السطر'})
            continue
        t = st['voice']['takes'][x['take']]
        a = V.decode(studio.path(pid, t['wav']).read_bytes())
        rms, peak = float(np.sqrt(np.mean(a ** 2))) if len(a) else 0.0, float(np.max(np.abs(a))) if len(a) else 0.0
        n = len(t['words']) or 1
        speech = max(0.1, t['seconds'] - (t.get('processed') or {}).get('pause_before', 0) - (t.get('processed') or {}).get('pause_after', 0))
        rate = round(n / speech, 2)
        res = {'rate_wps': rate, 'rms_db': _db(rms), 'peak_db': _db(peak), 'seconds': t['seconds'], 'not_heard': t.get('not_heard') or []}
        by_take[t['id']] = res
        if rate > 3.4: flags.append({'id': f'q-{t["id"]}-fast', 'line': lid, 'take': t['id'], 'code': 'TOO_FAST', 'severity': 'minor', 'status': 'open',
                                     'detail': f'{rate} words per second', 'detail_ar': f'{rate} كلمة في الثانية: سريع'})
        if rate < 1.0: flags.append({'id': f'q-{t["id"]}-slow', 'line': lid, 'take': t['id'], 'code': 'TOO_SLOW', 'severity': 'minor', 'status': 'open',
                                     'detail': f'{rate} words per second', 'detail_ar': f'{rate} كلمة في الثانية: بطيء'})
        if res['rms_db'] < -32: flags.append({'id': f'q-{t["id"]}-low', 'line': lid, 'take': t['id'], 'code': 'LOW_LEVEL', 'severity': 'minor', 'status': 'open',
                                              'detail': f'quiet ({res["rms_db"]} dBFS)', 'detail_ar': 'الصوت منخفض'})
        if peak >= 0.99: flags.append({'id': f'q-{t["id"]}-clip', 'line': lid, 'take': t['id'], 'code': 'CLIPPING', 'severity': 'minor', 'status': 'open',
                                       'detail': 'the audio clips', 'detail_ar': 'تشويش من ارتفاع الصوت'})
        for wi, w in enumerate(t['words']):
            if w.get('est') and t.get('not_heard') and w['w'] in t['not_heard']:
                flags.append({'id': f'q-{t["id"]}-w{wi}', 'line': lid, 'take': t['id'], 'wi': wi, 'word': w['w'], 'code': 'UNCERTAIN_WORD',
                              'severity': 'minor', 'status': 'open', 's': w['s'], 'e': w['e'],
                              'detail': f'the transcription did not hear «{w["w"]}»: listen to it', 'detail_ar': f'لم يُسمع «{w["w"]}» بوضوح: استمع إليها'})
    return {'flags': flags, 'by_take': by_take}


def mix(studio, pid, task=None) -> dict:
    """Job: the play-all narration for the current takes, with QA."""
    st = studio.state(pid)
    vl = st['voice'].get('lines') or {}
    eff = effective_takes(st)
    parts, segs, t = [], [], 0.0
    gap = np.zeros(int(V.SR * GAP))
    for lid, x in vl.items():
        if not eff.get(lid): continue
        tk = st['voice']['takes'][eff[lid]]
        a = V.decode(studio.path(pid, tk['wav']).read_bytes())
        segs.append({'line': lid, 'take': tk['id'], 'start': round(t, 3), 'end': round(t + len(a) / V.SR, 3), 'text': x['text'],
                     'status': tk['status'], 'words': [{'w': w['w'], 's': round(t + w['s'], 3), 'e': round(t + w['e'], 3), 'est': bool(w.get('est'))} for w in tk['words']],
                     'label': tk.get('label', '')})
        parts += [a, gap]
        t += len(a) / V.SR + GAP
        if task: task.unit(scene=lid)
    allv = np.concatenate(parts) if parts else np.zeros(1)
    rec = {'file': studio.put(pid, V.encode(allv, 'mp3'), 'mp3'), 'seconds': round(len(allv) / V.SR, 2), 'segments': segs,
           'takes': {s['line']: s['take'] for s in segs}, 'qa': qa(studio, pid, st),
           'label': 'DRAFT VOICE (gTTS, free) — not the final ElevenLabs voice'}
    studio.act(pid, 'cp_voice_mix', rec, actor='system')
    return {'seconds': rec['seconds'], 'lines': len(segs), 'flags': len(rec['qa']['flags'])}


def adjust(studio, pid, task, line, take, speed=1.0, pause_before=0.0, pause_after=0.0):
    """Job: speed and pauses for one line, as a new (processed) take of the same text."""
    st = studio.state(pid)
    base = st['voice']['takes'][take]
    tid = f'{base["id"]}-a' + hashlib.sha256(json.dumps([speed, pause_before, pause_after]).encode()).hexdigest()[:6]
    if tid in st['voice']['takes']:
        task.unit(scene=line, reused=True)
        return {'take': tid, 'reused': True}
    a = V.decode(studio.path(pid, base['wav']).read_bytes())
    if speed != 1.0:
        raw = V._ff('-f', 'f64le', '-ar', V.SR, '-ac', 1, '-i', '-', '-af', f'atempo={speed}', '-f', 'f64le', '-', inp=a.tobytes())
        a = np.frombuffer(raw, np.float64)
    a = np.concatenate([np.zeros(int(V.SR * pause_before)), a, np.zeros(int(V.SR * pause_after))])
    sh = lambda x: round(pause_before + x / speed, 3)
    words = [dict(w, s=sh(w['s']), e=sh(w['e'])) for w in base['words']]
    wav, mp3 = V.encode(a, 'wav'), V.encode(a, 'mp3')
    rec = {**{k: base[k] for k in ('line', 'text', 'spoken', 'script_v', 'library_version', 'heard', 'rules_applied') if k in base},
           'id': tid, 'provider': 'gtts+ffmpeg', 'label': LABEL_ADJ, 'audio': studio.put(pid, mp3, 'mp3'), 'wav': studio.put(pid, wav, 'wav'),
           'seconds': round(len(a) / V.SR, 3), 'words': words, 'not_heard': base.get('not_heard', []), 'peaks': V.peaks(a),
           'supersedes': st['voice']['by_line'].get(line, [None])[-1], 'reason': f'speed {speed}, pauses {pause_before}/{pause_after} s (processed locally)',
           'audio_sig': hashlib.sha256(np.round(a, 3).tobytes()).hexdigest()[:20], 'same_audio_as': None,
           'processed': {'from': base['id'], 'speed': speed, 'pause_before': pause_before, 'pause_after': pause_after, 'tool': 'ffmpeg atempo + silence'}}
    studio.act(pid, 'voice_take', rec, actor='system')
    task.unit(scene=line)
    return {'take': tid}
