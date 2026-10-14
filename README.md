# Video Director — development workspace

Isolated from every production repository. Local git only (no remote). Media never enters git; evidence and
stores live under `var/` (git-ignored).

## Safety rules enforced in code
- Paid voice generation exists only in `director/voice/gateway.py`: off unless `VIDEO_DIRECTOR_PAID_ENABLED=1`,
  single-use approval bound to the exact plan hash, expiry, budget check, no retries, results stored as candidates.
- Paid providers refuse any caller except the gateway. Tests use a mock transport and block all network access.
- Takes are content-addressed, write-once, read-only on disk; status changes are append-only events.
- Art modules (`director/art/`) cannot import the voice modules or the gateway (tested).
- Time Keeper and Diabetes History profiles, library scopes and voices are separate; a contamination check scans
  project files and the reviewer checks rendered colours.

## Modules
| Path | Milestone | What it does |
|---|---|---|
| `director/library.py` | M1 | Pronunciation library: scoped, versioned, provider rules; prefix- and diacritic-safe matching; ARTICLE_DROPPED check |
| `director/importers.py` | M1 | Read-only import of tts_habibi PRON (parsed, never executed), `_arabic` overrides, arabic_tts lexicon |
| `director/voice/takes.py` | M1 | Immutable take store |
| `director/voice/plan.py` | M1 | Cost plan: reuse / review / blocked / new, exact characters, plan hash |
| `director/voice/gateway.py` | M1 | The only path to paid generation (mock-tested) |
| `director/voice/imports.py` | M1 | Import approved ElevenLabs manifests + audio as approved takes |
| `director/ledger.py` | M1 | Budgets, approvals, spend, audit log (SQLite, outside git) |
| `director/profiles.py`, `profiles/*.yaml` | M1/M2 | Creative + voice profiles (draft v0), contamination check, per-film voice rules |
| `art/techniques.yaml`, `director/art/selector.py` | M2 | Visual Technique Registry; ranked options per scene with explicit exclusions; decision log |
| `director/art/review.py` | M3 | Art Reviewer: evidence packs from real renders, technical pass, review packets per stage/perspective |

## Run
    ./run_tests.sh            # 55 tests, network blocked, no credentials read

## Studio (M7): a new video from an idea — development only
Open `http://127.0.0.1:<port>/studio` on the local dashboard server (the review dashboard links to it: "＋ New video").
Steps: Research → Script → Hook → Draft voice → Art → Storyboard → Draft video → Review → Final voice plan, with a
project home (latest playable draft, scene strip, measured times, blockers) and one Inbox for every open decision.

| Path | What it does |
|---|---|
| `director/studio/store.py` | Event-sourced project state (append-only `studio` events + read-only content-addressed files); every rule (brand isolation, select ≠ approve, final approvals, one-word corrections, duplicates) |
| `director/studio/checks.py` | Script checks: spelling near-misses, unsupported claims from the research file, digits/Latin in narration, names to listen for |
| `director/studio/voice.py` | Free draft voice (gTTS, labelled DRAFT), whisper word timings aligned to the script, waveform, one-line re-takes after a pronunciation rule |
| `director/studio/art.py` | Technique builders for the Time Keeper paper engine; concepts, revisions, support matrix; never fabricates photos |
| `director/studio/storyboard.py` | Storyboard from approved items, draft render (vendor/paper-story, 1080×1920, -14 LUFS, WebM preview, TK end card) |
| `director/studio/review.py` | Independent review of a render (technical pass, layout, A/V sync by cross-correlation, history, readability, style) |
| `director/studio/gate.py` | Final ElevenLabs plan with blockers; never imports the paid gateway |
| `director/studio/api.py`, `studio.html` | HTTP actions/jobs and the page |
| `vendor/paper-story/` | Read-only copy of Time Keeper's renderer + end card (hashes in PROVENANCE.sha256) |

UAT: `tools/uat_full.sh` (fresh copy, whole journey through the UI, server killed mid-task, defect copy);
`tools/uat_defects.py` (planted defects); `tools/uat_report.py` (report). Unit tests: `tests/test_studio.py`.
