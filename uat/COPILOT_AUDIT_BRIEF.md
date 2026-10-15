# Independent audit brief — Co-Pilot mode (branch `copilot-mode`)

You did not write this code. Your job is to find where it does not do what the owner asked, with evidence.
Report every requirement as PASS / FAIL / PARTIAL / BLOCKED / NOT TESTED, and separate:
real product defects, test-harness mistakes, and limitations. Do not mark something PASS because the code looks
right: run it, call it, or read the recorded evidence.

## Hard rules (do not break these while auditing)
- No paid generation of any kind. Do not set `VIDEO_DIRECTOR_PAID_ENABLED=1`. Do not set `VD_AI_REAL_ENABLED=1`
  (a real headless Claude call costs money; the owner has not authorized an AI budget). Do not call ElevenLabs.
- Do not modify `var/preserved/`, `var/uat/`, `var/audit/AUDIT_REPORT*.md`, branch `uat-frozen-95a8646`.
- Do not modify product code. Write your own scripts only under `var/audit-copilot/`.
- Use a NEW server folder for anything you try: `tools/copilot_server.sh fresh <PORT> <new folder> [seed folder]`.
  You may seed from a copy of an existing acceptance folder; never point at the acceptance folders themselves.

## What the owner asked for (summary — check each)
1. Mode selector Manual / Co-Pilot / Auto, Co-Pilot default, Auto "not yet implemented"; mode stored; existing
   projects never changed; switch to Manual at any time without erasing approvals or bypassing gates.
2. Gates G1 direction, G2 script+hook, G3 voice, G4 visual style, G5 final creative approval, G6 paid narration.
   Resume automatically after a gate approval and after a server restart. Show stage, next action, blockers,
   scene progress. Processing time separate from waiting time; no invented ETA.
3. Approval-state engine: states (not started, working, AI review, needs owner, changes requested, owner approved,
   blocked, outdated, completed); records with item/version, approver, timestamp, content hash, settings hash;
   targeted invalidation; never carry an approval to changed content; earlier approved output kept until its
   replacement is reviewed. AI-reviewed never shown as owner-approved.
4. Script: fact check + separate quality review + self-revision; unsupported claims never silently approved;
   sentence editor, hook comparison, source-backed warnings; only the approved version used downstream.
   Do not rely on keyword matching alone for facts (Rolex regressions: the 7 missed paraphrases and the false
   positive «في أول مرة نزلت فيها الساعة إلى الماء…»; generic override reasons must not pass).
5. Voice: play-all, word tap, spelling/tashkeel/pronunciation correction, speed/pause (free local, labelled),
   version comparison, approval; draft voice clearly not ElevenLabs; corrections never overwrite approved takes.
6. Visual: ≥3 directions with real boards, evaluated and recommended, exact approved style recorded.
7. Pictures: provenance, licence evidence (never treated as licensed without evidence), owner uploads at any time,
   exception for unlicensed pictures; never invent genuine historical photos.
8. Scenes: render → technical check → independent art review → safe fixes → re-render, max two correction rounds,
   escalate (critical fact, rights, unfixable, touches approved, retry limit); all versions and evidence kept.
9. Film: opening frame, hook, end card, aspect, levels, timing, overlaps, consistency; technical + creative review;
   Gate 5 with synced timeline, approve/reject/time-coded comments → targeted scene tasks; critical issues must be
   resolved and minor ones explicitly acknowledged.
10. Paid: G6 shows exact text, voice/model, lines, characters, budget; single-use approval bound to plan hash,
    expires on change; no automatic paid retries; rejected when missing/outdated/exhausted/over budget;
    append-only ledger; zero paid generation by default. No automatic spending, publishing or production integration.
11. AI worker: verify the claims about headless Claude Code in `director/copilot/ai.py` WITHOUT making a real call:
    zero default budget, second environment lock, per-call cap, cost recorded on failure, no retries.
12. iPhone-first Arabic UI; no sideways scrolling; dashboard secondary.

## Evidence available
- Unit tests: `./run_tests.sh` (all) and `python3 -m unittest tests.test_copilot`.
- Browser acceptance run: `../cp-dev/e2e1-out/results.json` + screenshots; server folder `../cp-dev/e2e1`
  (read only — copy it if you want to experiment).
- Full-size headless run: `../cp-dev/var3` and its log `../cp-dev/var3.log`.
- Frozen product of the earlier UAT: branch `uat-frozen-95a8646`; evidence checksums in `var/preserved/`.

Write your report to `var/audit-copilot/AUDIT_REPORT.md` (requirement table, defects with reproduction steps,
harness mistakes, limitations, and anything you could not test and why).
