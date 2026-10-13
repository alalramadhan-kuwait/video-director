"""Import what happened before the event log existed, as RECONSTRUCTED events with their evidence.

Only three kinds of evidence are used, all read-only:
  * file modification times of the episode's own outputs (ep7);
  * git commit dates and messages of the published Royal Oak project (audit clone);
  * the provider's own generation time for each approved take (ElevenLabs history saved in Phase 0.5).
Stage statuses are set only where a recorded decision supports them; everything else stays 'unknown'.
Running the import twice adds nothing (it skips evidence already imported).
"""
from __future__ import annotations
import json, os, subprocess, time
from pathlib import Path

from ..events import EventLog


def _mtime(p: Path) -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(os.stat(p).st_mtime))


def _have(log: EventLog, evidence: str) -> bool:
    return any(r['evidence'] == evidence for r in log.rows())


def import_ep7(log: EventLog, S: Path):
    ep = S / 'ep7'; P, V = 'diabetes-history', 'ep7'
    files = [('script', 'PLAN.md', 'episode plan written'), ('script', 'script.min.json', 'script finalised (30 lines)'),
             ('voice', 'tts_work/run_v3.json', 'voice: final take selection (round 3)'),
             ('voice', 'tts_work/final/full.mp3', 'voice: final narration assembled'),
             ('render', 'out/ep7_part3.mp4', 'render: part 3'), ('render', 'out/ep7_part1.mp4', 'render: part 1'),
             ('render', 'out/ep7_part2.mp4', 'render: part 2 (after the b1 fixes)'),
             ('render', 'out/ep7_tiktok_full.mp4', 'render: full TikTok version'),
             ('render', 'out/ep7_tiktok_full_29mb.mp4', 'render: TikTok upload file (≤ 29 MB)')]
    for stage, rel, what in files:
        ev = f'file time: ep7/{rel}'
        if (ep / rel).exists() and not _have(log, ev):
            log.emit('revision', P, video=V, stage=stage, source='reconstructed', evidence=ev, at=_mtime(ep / rel), what=what)
    revs = [('b1', 'chk/p2b.png', 'b1 check: «مدة أطول» chip hidden under the caption'),
            ('b1', 'chk/p2c.png', 'b1 check: doctor name moved, now over the year card'),
            ('b1', 'chk/p2d.png', 'b1 check: name and chip both clear (used in the final)')]
    for scene, rel, what in revs:
        ev = f'file time: ep7/{rel}'
        if (ep / rel).exists() and not _have(log, ev):
            log.emit('revision', P, video=V, scene=scene, stage='art', source='reconstructed', evidence=ev,
                     at=_mtime(ep / rel), what=what)
    # stage statuses backed by a recorded decision (or explicitly unknown)
    statuses = [
        ('script', 'unknown', 'no script approval was recorded separately from the voice review'),
        ('voice', 'approved', 'voice review round 3 ended with 0 marks and the owner replied «ممتاز» (2026-10-12)'),
        ('art', 'waiting_review', 'art review M4: 44 AI recommendations waiting for the owner'),
        ('render', 'waiting_review', 'render files exist and pass the automated checks; reviewed as part of the final'),
        ('final', 'waiting_review', 'final files delivered 2026-10-12; no final approval recorded'),
        ('publish', 'blocked', 'owner decision (Phase 0.5): do not publish until the Fasih licence (CPML) is reviewed'),
    ]
    for stage, status, why in statuses:
        ev = f'status: ep7/{stage}'
        if not _have(log, ev):
            log.emit('stage_status', P, video=V, stage=stage, status=status, source='reconstructed', evidence=ev, why=why)
    # the voice approval happened before the final narration was assembled; date it by that file, not by the import
    ev, f = 'status: ep7/voice (dated by the final narration file)', ep / 'tts_work/final/full.mp3'
    if f.exists() and not _have(log, ev):
        log.emit('stage_status', P, video=V, stage='voice', status='approved', source='reconstructed', evidence=ev,
                 at=_mtime(f), why='owner approved the voice after review round 3 (0 marks, «ممتاز»); the final narration '
                                   'was assembled from the approved takes at this time')


def import_royal_oak(log: EventLog, S: Path):
    P, V = 'timekeeper', 'royal-oak'
    clone = S / 'audit/claude_success-story-video'
    out = subprocess.run(['git', '-C', str(clone), 'log', '--date=iso-strict', '--format=%ad%x09%h%x09%s', '--',
                          'video/royal-oak'], capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        at, h, msg = line.split('\t', 2)
        ev = f'git commit {h}'
        if _have(log, ev): continue
        low = msg.lower()
        stage = ('voice' if any(k in low for k in ('voice', 're-recorded', 'voiced', 'read in arabic', 'abdullah', 'pron'))
                 else 'script' if 'script' in low or 'wording' in low
                 else 'art' if any(k in low for k in ('print', 'frame', 'face', 'cover', 'scene', 'storyboard', 'hook', 'end card', 'crop'))
                 else 'other')
        t = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(_parse_iso(at)))
        log.emit('revision', P, video=V, stage=stage, source='reconstructed', evidence=ev, at=t, what=msg)
    # the final narration, take by take, from the provider's own generation times
    meta = sorted((S / 'phase05/royal-oak/meta').glob('*.json'))
    if meta and not _have(log, 'provider history: Royal Oak final narration'):
        items = []
        for m in meta:
            d = json.loads(m.read_text(encoding='utf-8'))
            items.append((d['history_item']['date_unix'], d['key'], len(d['history_item']['text'])))
        items.sort()
        log.emit('revision', P, video=V, stage='voice', source='reconstructed', evidence='provider history: Royal Oak final narration',
                 at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(items[0][0])),
                 what=f'final narration: {len(items)} approved takes generated between '
                      f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(items[0][0]))} and "
                      f"{time.strftime('%Y-%m-%d %H:%M', time.gmtime(items[-1][0]))} UTC",
                 takes=[{'line': k, 'at': u, 'chars': c} for u, k, c in items])
    statuses = [('script', 'unknown', 'owner-approved wording is recorded for some lines in git, not for the whole script'),
                ('voice', 'waiting_review', '30 approved takes; 8 lines wait for a listening check (article in Steel/Quartz/White Gold)'),
                ('art', 'unknown', 'storyboards exist; the photographs are not in this workspace'),
                ('render', 'unknown', 'no render files in this workspace'),
                ('final', 'unknown', 'no final approval recorded here'), ('publish', 'unknown', 'not recorded here')]
    for stage, status, why in statuses:
        ev = f'status: royal-oak/{stage}'
        if not _have(log, ev):
            log.emit('stage_status', P, video=V, stage=stage, status=status, source='reconstructed', evidence=ev, why=why)


def _parse_iso(s):
    from datetime import datetime
    return datetime.fromisoformat(s).timestamp()
