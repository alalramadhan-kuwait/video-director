"""Proof that a listening answer was given while the audio really played.

The page sends, with every listening answer, what the browser itself reports about the audio element:
    {src, duration, played: [[start, end], ...], error: null}
`played` is the element's own TimeRanges of audio actually played. An answer counts as a confirmed listening result
only if:
  * the source is this check's own audio file;
  * the file loaded: the duration the browser reports matches the file's real duration (±0.25 s);
  * the played ranges cover at least 80 % of the flagged word (with 0.15 s of context before it).
A failed load can still be reported (decision 'playback_failed'), but it is never a listening result.
"""
from __future__ import annotations

LISTENING = {'article_heard', 'article_missing', 'unsure'}
MIN_COVER = 0.8


def covered(ranges, s, e) -> float:
    if e <= s:
        return 0.0
    tot = 0.0
    for a, b in ranges or []:
        lo, hi = max(a, s), min(b, e)
        if hi > lo:
            tot += hi - lo
    return tot / (e - s)


def check_listening_evidence(target: dict | None, playback: dict | None) -> tuple[bool, str]:
    if not target:
        return False, 'not a listening check'
    if not playback:
        return False, 'no playback record: the audio was not played on this page'
    if playback.get('error'):
        return False, f"the audio failed to play ({playback['error']})"
    src = str(playback.get('src') or '')
    if not src.endswith(target['audio_file']):
        return False, f"played {src.rsplit('/', 1)[-1] or 'nothing'}, not {target['audio_file']}"
    dur = playback.get('duration')
    if not isinstance(dur, (int, float)) or abs(dur - target['duration']) > 0.25:
        return False, f"audio did not load fully (duration {dur} vs {target['duration']})"
    c = covered(playback.get('played'), max(0.0, target['word_s'] - 0.15), target['word_e'])
    if c < MIN_COVER:
        return False, f'the flagged word was not played ({int(c * 100)} % of it heard)'
    return True, f'played {int(c * 100)} % of the flagged word'
