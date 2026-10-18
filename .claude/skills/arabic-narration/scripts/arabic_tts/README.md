# arabic_tts — Arabic narration with Fasih-TTS-V1, checked word by word

Four phases on top of a fixed engine (model, voice and settings never change):

| Module | Phase | What it does |
|---|---|---|
| `diacritize.py` | 1 | Full contextual diacritization (written by Claude per sentence) + safeguards: letters locked to the original, malformed marks, author's marks, case-ending heuristics, coverage, protected terms, CATT second opinion |
| `lexicon.py` | 2 | Project pronunciation lexicon (`examples/lexicon.template.yaml`): approved stems, context rules, `plain`, `spoken`, `avoid` |
| `preprocess.py` | 4 | Spoken-only text: abbreviations, years → genitive words, quotes / trailing ellipsis, per-line overrides |
| `select.py` | 3 | Take selection: phonemes (wav2vec2) + Whisper completeness + truncation / repetition / extra speech + `avoid` patterns; flags uncertain lines |
| `run.py`, `batch.py`, `engine.py` | — | Seeded synthesis with cache; `--select baseline` reproduces the old Whisper-only choice for fair comparisons |
| `assemble.py`, `review/` | — | Full-episode narration + word-synced review page where the listener taps the wrong word |
| `hashguard.py` | — | Snapshot / verify hashes of approved audio |

Guide, workflow and the lessons behind every rule: `../../SKILL.md` and `../../references/`.
Tests: `python -m arabic_tts.tests.test_phase1|test_phase2|test_phase4` (run from `motion/`).
License note: Fasih-TTS-V1 is CPML (non-commercial, including generated audio).
