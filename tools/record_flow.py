"""Record a film's narration as continuous takes, one per act, then split it into one take per line.

The owner, on the rubies film: «the video is not connected… jumping from scene to scene without any transition in the
wording and also in the sound». A voice read line by line starts afresh on every line: its pitch and energy reset at
each cut. Read as one paragraph per act, the voice carries the story across the cuts; the lines are then cut apart in
the silences between them, on the timings ElevenLabs returns with the audio, so the film still has one take per line.

    python3 tools/record_flow.py films/<film>.yaml <voice_dir> --voice <voice_id> [--name "Voice name"] [--seed 1234]

An act starts at each line marked `act: true` (the first line starts act one). Each act is read with the act before it
as `previous_text` and the act after it as `next_text`, so the acts join too. The key comes from ELEVENLABS_API_KEY,
or from the session's proxy. Natural speed only: a voice is never sped up (cut the script instead). Check every line
with Whisper afterwards; a cloned voice can add words.
"""
from __future__ import annotations

import argparse, base64, json, os, subprocess, sys, tempfile, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from director import brand as B, quickfilm  # noqa: E402

SR = 24000
SETTINGS = {'stability': .4, 'similarity_boost': .8, 'style': .2, 'use_speaker_boost': True, 'speed': 1.0}
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


def speak(voice: str, text: str, prev: str | None, nxt: str | None, seed: int, model: str) -> dict:
    body = {'text': text, 'model_id': model, 'seed': seed, 'voice_settings': SETTINGS}
    if prev: body['previous_text'] = prev
    if nxt: body['next_text'] = nxt
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(body, f, ensure_ascii=False); req = f.name
    cmd = ['curl', '-sS', '--max-time', '300', '-H', 'Content-Type: application/json', '-X', 'POST',
           f'https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128', '--data-binary', '@' + req]
    if os.environ.get('ELEVENLABS_API_KEY'): cmd[1:1] = ['-H', 'xi-api-key: ' + os.environ['ELEVENLABS_API_KEY']]
    r = subprocess.run(cmd, capture_output=True, text=True, check=True)
    os.unlink(req)
    d = json.loads(r.stdout)
    if 'audio_base64' not in d: raise RuntimeError(f'ElevenLabs: {r.stdout[:300]}')
    return d


def pcm(mp3: bytes) -> bytes:
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'pipe:0', '-ar', str(SR), '-ac', '1', '-f', 's16le', 'pipe:1'],
                       input=mp3, capture_output=True, check=True)
    return r.stdout


def write_wav(path: Path, data: bytes) -> None:
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('film'); ap.add_argument('out')
    ap.add_argument('--voice', required=True); ap.add_argument('--name', default='')
    ap.add_argument('--seed', type=int, default=1234); ap.add_argument('--model', default='eleven_multilingual_v2')
    a = ap.parse_args(argv)
    film = quickfilm.load(a.film); brand = film.get('brand', 'timekeeper')
    out = Path(a.out); (out / 'raw').mkdir(parents=True, exist_ok=True)
    groups = acts(film['lines'])
    said = [[B.spoken(ln.get('say') or ln['text'], brand) for ln in g] for g in groups]
    paras = [paragraph(t) for t in said]
    for k, (g, (text, spans)) in enumerate(zip(groups, paras)):
        d = speak(a.voice, text, paras[k - 1][0] if k else None, paras[k + 1][0] if k + 1 < len(paras) else None, a.seed, a.model)
        al = d.get('alignment') or {}
        chars, st, en = al.get('characters', []), al.get('character_start_times_seconds', []), al.get('character_end_times_seconds', [])
        if ''.join(chars) != text: raise RuntimeError(f'act {k + 1}: the timings do not follow the text ({len(chars)} vs {len(text)} characters)')
        mp3 = base64.b64decode(d['audio_base64']); (out / 'raw' / f'act{k + 1}.mp3').write_bytes(mp3)
        audio = pcm(mp3); total = len(audio) / 2 / SR
        for ln, (t0, t1), spoken in zip(g, cuts(spans, st, en, total), said[k]):
            i0, i1 = int(t0 * SR) * 2, int(t1 * SR) * 2
            write_wav(out / f"{ln['id']}.wav", audio[i0:i1])
            (out / f"{ln['id']}.json").write_text(json.dumps({'provider': 'elevenlabs', 'voice_id': a.voice, 'voice_name': a.name,
                                                               'model': a.model, 'act': k + 1, 'from': t0, 'to': t1, 'text': spoken},
                                                              ensure_ascii=False), encoding='utf-8')
            print(f"act {k + 1}  {ln['id']:>5}  {t0:6.2f}-{t1:6.2f}  {spoken}", flush=True)
    print('characters', sum(len(p[0]) for p in paras))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
