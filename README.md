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
