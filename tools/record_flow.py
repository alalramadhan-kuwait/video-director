"""Record a film's narration as ONE take of the whole script, then cut it into one take per line.

The owner, 2 Nov 2026: «The narrator is telling one continuous story, not performing each scene independently» and
«النص الكامل ← توليد صوت واحد ← استخراج توقيت الجمل والكلمات ← إنشاء المشاهد حسب المعنى ← مزامنة المشاهد مع
الصوت». So the whole script is read in one pass (one voice, one energy that develops with the story), the lines are cut
apart in the middle of the silences between them on the timings ElevenLabs returns with the audio, and each piece keeps
its share of the pauses: make_film lays the scenes on that audio end to end (`continuous` in each piece's record), so
the narration plays exactly as it was read and the pictures follow it.

    python3 tools/record_flow.py films/<film>.yaml <voice_dir> --voice <voice_id> [--name "Voice name"] [--seed 1234]

A studio film without a .yaml records from its script as JSON: {"lines": [{"n", "text", "say"?, "screen"?}], "rules_ok"?,
"kw_ok"?} (the record's `script.lines`, with `say` where the voice needs a different spelling).

THE VOICE GATE (the owner, 10 Nov 2026: «there should be a gateway where if the rules are not applied it will not
record»): this tool is the only way a take is made; ElevenLabs is never called any other way. Before anything is paid
for, director/voice_gate.py checks the words on screen and the exact text the voice will get (no digits, no English
letters except names said in their own language and words the owner cleared by ear, no «ال» before an English word, no
«گ»): those checks have no override. The house rules, the word book and the delivery plan stop it too; their overrides
need the owner's own words (--why), saved with the take in gate.json.

Before anything is paid for, the script's delivery plan is checked (director/narration.py: each line's `tone:`, the
arc across the film); a broken arc stops the recording unless --anyway. A script over MAX_CHARS is read act by act
(`act: true` lines), each act with the acts around it as context, the same voice settings throughout. Natural speed
only: a voice is never sped up (cut the script instead). Afterwards: tools/hear.py for the words, and
tools/hear_flow.py for one performance (it also writes the narration alone as an MP4 to listen to without the film).
"""
from __future__ import annotations

import argparse, base64, json, os, subprocess, sys, tempfile, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from director import brand as B, house, kw, narration, quickfilm, voice_gate  # noqa: E402

SR = 24000
SETTINGS = {'stability': .5, 'similarity_boost': .8, 'style': .15, 'use_speaker_boost': True, 'speed': 1.0}   # steadier: one character all through
MAX_CHARS = 4500                       # a longer script is read act by act, with context
END = '.؟?!…:،,'


def acts(lines: list[dict]) -> list[list[dict]]:
    """The film's lines grouped into acts: a new act at each `act: true` line."""
    out: list[list[dict]] = []
    for ln in lines:
        if ln.get('act') or not out: out.append([])
        out[-1].append(ln)
    return out


def paragraph(texts: list[str]) -> tuple[str, list[tuple[int, int]]]:
    """The act's lines as one paragraph (a full stop after a line that has no end of its own) and each line's
    [start, end) in it."""
    parts, spans, at = [], [], 0
    for t in texts:
        t = t.strip()
        if t[-1:] not in END: t += '.'
        spans.append((at, at + len(t))); parts.append(t); at += len(t) + 1
    return ' '.join(parts), spans


def cuts(spans: list[tuple[int, int]], starts: list[float], ends: list[float], total: float) -> list[tuple[float, float]]:
    """Each line's [from, to) seconds in the take: cut in the middle of the silence between one line's last sound and
    the next line's first."""
    def last(a, b):
        return max(ends[i] for i in range(a, b))
    def first(a, b):
        return min(starts[i] for i in range(a, b))
    bounds = [0.0]
    for (a0, a1), (b0, b1) in zip(spans, spans[1:]):
        bounds.append(round((last(a0, a1) + first(b0, b1)) / 2, 3))
    bounds.append(total)
    return list(zip(bounds, bounds[1:]))


V3 = 'eleven_v3'
SETTINGS_V3 = {'stability': .5, 'similarity_boost': .8, 'speed': .8}   # «Natural»; v3 takes no style or speaker boost


def tagged(ln: dict, spoken: str, model: str) -> str:
    """The line as the voice reads it: on eleven_v3 its `emotion:` goes in front as an audio tag («[calm, curious] …»),
    which the voice performs and never says (the owner, 2 Nov 2026, choosing Faisal on v3 with emotion: «اعتمد ٢»).
    The screen and the captions keep `text`."""
    e = (ln.get('emotion') or '').strip()
    return f'[{e}] {spoken}' if e and model == V3 else spoken


def speak(voice: str, text: str, prev: str | None, nxt: str | None, seed: int, model: str) -> dict:
    body = {'text': text, 'model_id': model, 'seed': seed, 'voice_settings': SETTINGS}
    if model == V3: body.pop('seed'); prev = nxt = None      # v3 reads the whole take at once, without context fields
    if prev: body['previous_text'] = prev
    if nxt: body['next_text'] = nxt
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(body, f, ensure_ascii=False); req = f.name
    stream = model == V3          # a long v3 take outlasts the proxy's wait for a whole answer: it is streamed in pieces
    cmd = ['curl', '-sS', '-N', '--max-time', '600', '-H', 'Content-Type: application/json', '-X', 'POST',
           f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/{'stream/' if stream else ''}with-timestamps?output_format=mp3_44100_128",
           '--data-binary', '@' + req]
    if os.environ.get('ELEVENLABS_API_KEY'): cmd[1:1] = ['-H', 'xi-api-key: ' + os.environ['ELEVENLABS_API_KEY']]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    os.unlink(req)
    d = joined(r.stdout) if stream else json.loads(r.stdout)
    if 'audio_base64' not in d: raise RuntimeError(f'ElevenLabs: {r.stdout[:300]}')
    return d


def joined(ndjson: str) -> dict:
    """A streamed answer (one JSON object a line: a piece of audio and the timings of its characters, in seconds from
    the start) as one answer: the audio end to end, the timings in order."""
    parts = [json.loads(x) for x in ndjson.splitlines() if x.strip()]
    if not parts or not any('audio_base64' in p for p in parts): raise RuntimeError(f'ElevenLabs: {ndjson[:300]}')
    audio = b''.join(base64.b64decode(p['audio_base64']) for p in parts if p.get('audio_base64'))
    al = {'characters': [], 'character_start_times_seconds': [], 'character_end_times_seconds': []}
    for p in parts:
        for k in al: al[k] += (p.get('alignment') or {}).get(k) or []
    return {'audio_base64': base64.b64encode(audio).decode(), 'alignment': al}


def pcm(mp3: bytes) -> bytes:
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-ar', str(SR), '-ac', '1', '-f', 's16le', 'pipe:1'],
                       input=mp3, capture_output=True, check=True)
    return r.stdout


def write_wav(path: Path, data: bytes) -> None:
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data)


def load(path: str) -> tuple[dict, bool]:
    """The film and whether it is in the house style: a .yaml film, or a studio script as JSON."""
    if str(path).endswith('.json'):
        d = json.loads(Path(path).read_text(encoding='utf-8'))
        lines = [{'id': f"l{l.get('n', k + 1)}", 'text': l['text'], **({'say': l['say']} if l.get('say') else {}),
                  **({'screen': l['screen']} if l.get('screen') else {}), **({'act': True} if k == 0 else {})}
                 for k, l in enumerate(d['lines'])]
        return {'brand': d.get('brand', 'timekeeper'), 'title': d.get('title', ''), 'lines': lines,
                'rules_ok': d.get('rules_ok'), 'kw_ok': d.get('kw_ok'), 'names': d.get('names')}, True
    film = quickfilm.load(path)
    return film, quickfilm.house(film)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('film'); ap.add_argument('out')
    ap.add_argument('--voice', required=True); ap.add_argument('--name', default='')
    ap.add_argument('--seed', type=int, default=1234); ap.add_argument('--model', default='eleven_multilingual_v2')
    ap.add_argument('--per-act', action='store_true', help='read act by act even when the whole script fits one take')
    ap.add_argument('--anyway', action='store_true', help='record even when the delivery plan breaks one performance')
    ap.add_argument('--words-ok', action='store_true', help="record even with words the owner has not cleared (brand/kuwaiti-words.json)")
    ap.add_argument('--rules-ok', action='store_true', help='record even when the script breaks a house rule (brand/house_rules.yaml)')
    ap.add_argument('--why', default='', help="the owner's own words for an override (--anyway, --words-ok, --rules-ok); required with any of them")
    a = ap.parse_args(argv)
    if (a.anyway or a.words_ok or a.rules_ok) and not a.why.strip():
        print('an override needs the owner\'s own words: --why "<what he said>"'); return 6
    film, house_style = load(a.film); brand = film.get('brand', 'timekeeper')
    global SETTINGS
    if a.model == V3: SETTINGS = dict(SETTINGS_V3)
    SETTINGS = {**SETTINGS, **((film.get('voice') or {}).get('settings') or {})}   # the film's own voice settings win
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True)
    problems = narration.check(film['lines'])
    for p_ in problems: print('delivery:', p_)
    if problems and not a.anyway: print('the delivery plan breaks one performance: fix the tones (or --anyway)'); return 2
    # the owner's word book: his picks are written in, and any word he has not cleared stops the take before it is paid for
    flags = kw.check(film['lines'], film.get('kw_ok'))
    for f_ in flags:
        print(f"words: line {f_['line'] + 1}: «{f_['word']}»" + (f" → «{f_['say']}» ({f_.get('note', '')})" if f_['kind'] == 'ask' else ' is new: let the owner pick how it is said'))
    if flags and not a.words_ok: print('words the owner has not cleared: put them on his script card (or list them under kw_ok:, or --words-ok)'); return 3
    # the house rules gate: every owner correction a machine can check, before the take is paid for
    broken = house.check_lines(film['lines'], ok=film.get('rules_ok'))
    for b_ in broken: print('house rules:', b_)
    if broken and not a.rules_ok: print('the script breaks the house rules: fix it (tools/house_check.py --fix), or --rules-ok'); return 4
    for ln in film['lines']: ln['say'] = kw.apply(ln.get('say') or ln['text'])
    allsaid = [B.spoken(ln.get('say') or ln['text'], brand) for ln in film['lines']]
    # the voice gate: the words on screen and the exact text the voice gets; no override
    names = list(quickfilm.house_names(film).values()) if house_style else []
    gate = voice_gate.spoken_problems(allsaid, names=names) + (voice_gate.screen_problems(film['lines'], names=names) if house_style else [])
    (out / 'gate.json').write_text(json.dumps({'passed': not gate, 'problems': gate, 'house_rules': broken, 'words': flags,
                                               'delivery': problems, 'override_why': a.why}, ensure_ascii=False, indent=1), encoding='utf-8')
    for g_ in gate: print('voice gate:', g_)
    if gate: print('the voice gate stops the take: fix the script (nothing was paid for)'); return 5
    whole = sum(len(t) + 1 for t in allsaid) <= MAX_CHARS and not a.per_act
    groups = [film['lines']] if whole else acts(film['lines'])
    said = [[tagged(ln, B.spoken(ln.get('say') or ln['text'], brand), a.model) for ln in g] for g in groups]
    paras = [paragraph(t) for t in said]
    for k, (g, (text, spans)) in enumerate(zip(groups, paras)):
        d = speak(a.voice, text, paras[k - 1][0] if k else None, paras[k + 1][0] if k + 1 < len(paras) else None, a.seed, a.model)
        al = d.get('alignment') or {}
        chars, st, en = al.get('characters', []), al.get('character_start_times_seconds', []), al.get('character_end_times_seconds', [])
        if ''.join(chars) != text: raise RuntimeError(f'act {k + 1}: the timings do not follow the text ({len(chars)} vs {len(text)} characters)')
        name = 'whole' if whole else f'act{k + 1}'
        mp3 = base64.b64decode(d['audio_base64']); (out / 'raw' / f'{name}.mp3').write_bytes(mp3)
        (out / 'raw' / f'{name}.json').write_text(json.dumps({'text': text, 'alignment': al}, ensure_ascii=False), encoding='utf-8')
        audio = pcm(mp3); total = len(audio) / 2 / SR
        for ln, (t0, t1), spoken in zip(g, cuts(spans, st, en, total), said[k]):
            i0, i1 = int(t0 * SR) * 2, int(t1 * SR) * 2
            write_wav(out / f"{ln['id']}.wav", audio[i0:i1])
            (out / f"{ln['id']}.json").write_text(json.dumps({'provider': 'elevenlabs', 'voice_id': a.voice, 'voice_name': a.name,
                                                               'model': a.model, 'act': k + 1, 'from': t0, 'to': t1, 'text': spoken,
                                                               'master': f'raw/{name}.mp3', 'continuous': True, 'settings': SETTINGS},
                                                              ensure_ascii=False), encoding='utf-8')
            print(f"act {k + 1}  {ln['id']:>5}  {t0:6.2f}-{t1:6.2f}  {spoken}", flush=True)
    print('characters', sum(len(p[0]) for p in paras))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
