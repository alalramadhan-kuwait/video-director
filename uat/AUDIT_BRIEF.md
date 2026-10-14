# Independent audit brief — Video Director Studio, Rolex Oyster UAT

You are a second, independent tester. Another agent (the "first tester") built the Studio part of Video Director and
ran a user acceptance test. Your job is to check that work YOURSELF. Do not take the first tester's claims as true:
repeat the critical workflows, look for problems they missed, and challenge anything that is not supported by
evidence.

## The owner's original requirements (verbatim summary of what was asked)

Test Video Director as a real user creating a video from scratch: "The story of the Rolex Oyster and the development
of the first waterproof wristwatch." Use the actual interface; do not bypass it except to diagnose a failure.

* A. Create a Time Keeper project; select creative identity and ElevenLabs final-voice profile; only Time Keeper
  settings load (no Diabetes History art, voice or branding); saving, reopening and version history work.
* B. Research with reliable sources (Oyster 1926 vs earlier water-resistant watches, screw-down case, Mercedes Gleitze
  1927) — never claim Rolex invented the first waterproof watch unless sources support it. Arabic script for Time
  Keeper; several versions; a deliberate spelling/pronunciation mistake must be detected; the user can highlight the
  word, explain, request a correction; the correction changes only that text and keeps earlier versions.
* C. 3–4 hooks with spoken line, on-screen text and opening visual; a recommendation with reasons; selection recorded;
  the story delivers on the hook.
* D. ElevenLabs disabled. Free draft voice, clearly labelled. Narration-ready text, pronunciation dictionary, draft
  audio, waveform + transcript, word sync, tap a word to play it, flag a mispronounced word, save a correction, apply it
  to the right line, new take without changing other approved clips, compare old/new, approve/reject, decision saved
  and shown. Never claim the final ElevenLabs pronunciation is verified by another provider.
* E/F. Several genuinely different art concepts; supported vs needs-implementation vs paid; no fictional historical
  photos or inaccurate Rolex parts. Gallery: compare, full-screen, select, request modification, review revision,
  approve a specific version, see it in the right storyboard scene. Selecting must not approve.
* G. Storyboard from the approved script; durations from narration; transitions; a free/local draft render; captions,
  timing, sync, motion; Time Keeper end card; for Reels the video starts on a moving hook, not a frozen cover.
* H. Independent Art Reviewer: history, watch design, composition, Arabic captions, motion/pacing, style consistency,
  missing assets, overlaps, framing, A/V sync. Known defects planted in a disposable copy must be found with scene IDs,
  timecodes, evidence, severity, recommendations. Accepting creates a correction task; dismissing keeps history; approved
  artwork is never altered automatically.
* I. Progress dashboard: current stage, done/pending tasks, actual times, ETA only when measured, blockers, pending
  approvals, timeline, inbox counts, gallery selections, saving/reopening. Nothing approved just because a file exists.
* J. Final gate up to (not including) ElevenLabs: exact approved text, voice and model, billable characters, reuse of
  approved takes only when appropriate, explicit owner authorization, budget and single-use approvals, unauthorized
  generation rejected, zero paid calls.
* Failure recovery: rejected script, wrong pronunciation, rejected take, missing historical image, rejected art concept,
  requested revision, failed render, page refresh during review, duplicate approval, interrupted task, reopening after a
  restart, invalid/missing media, unauthorized paid call — without losing approved work.
* Classify each feature PASS / FAIL / PARTIAL / BLOCKED / NOT TESTED. A mocked backend test is not proof that a real
  provider works; an art description is not a generated image; a draft video is not a production video.

## Safety rules (hard)

* Work ONLY on the audit copy described below. Do not touch `var/dashboard/`, `var/dashboard-uat/`, any production
  repository (`/home/user/majedphotos/...`), the audit snapshot (`scratchpad/audit/...`), `phase05/` or approved media.
* Do not call ElevenLabs or any paid service; do not set `VIDEO_DIRECTOR_PAID_ENABLED=1`; do not read or print secrets.
* Do not publish, deploy or push anything. Do not edit the Studio's code: you are auditing, not fixing. You may write
  scripts and notes under `var/audit/` only.

## What you get

* Code: `director/studio/` (store, checks, voice, art, storyboard, engine, review, gate, api, studio.html),
  `director/dashboard/serve.py` (routes), tests in `tests/test_studio.py`, UAT driver `tools/uat_rolex.mjs`, defect
  harness `tools/uat_defects.py`.
* Running app (your own copy, already containing the first tester's finished Rolex Oyster project):
  `http://127.0.0.1:8768/studio` (local server; the main review dashboard is at `/`). It runs on
  `var/audit/var` (a copy). You may create new projects there, click everything, and break things.
* Restart it if needed: `tools/audit_server.sh restart` (keeps your copy) or `tools/audit_server.sh fresh` (a new copy of the finished UAT state). Manual equivalent:
  use: `env -u ELEVENLABS_API_KEY -u FAL_KEY VIDEO_DIRECTOR_PAID_ENABLED=0 VD_STUDIO_TEST=1 VD_DASHBOARD_VAR=$PWD/var/audit/var PYTHONPATH=$PWD nohup python3 -m director.dashboard.serve --port 8768 > var/audit/serve.log 2>&1 &`
  (kill the old one first: `ps -eo pid,comm,args | awk '$2=="python3" && /--port 8768/ {print $1}' | xargs -r kill`).
* Evidence from the first tester (to CHALLENGE, not to copy): `var/uat/results.json`, `var/uat/shots/`,
  `var/uat/defects.log` (defects they found and fixed), `var/uat/defects/defects.json` (planted-defect results),
  the draft film (see the project's latest render in the Studio).
* Playwright: `require('/opt/node22/lib/node_modules/playwright')`, Chromium at
  `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` (this Chromium cannot play H.264 MP4; the Studio also serves a
  WebM preview). iPhone size: `devices['iPhone 13']`. Desktop: 1366x900.
* Whisper (local, free) for listening by machine: `faster_whisper` with model `small` (cached).

## What to do

1. Repeat the critical workflows yourself in the UI (desktop AND iPhone sizes): create a NEW project of your own
   (any watch topic or a second Rolex project), add a script version through the API as the writer (the Studio has no
   writer), flag a word, apply a correction, choose a hook, make a draft read (gTTS needs network; if it fails, say so),
   tap words, flag and fix a pronunciation, approve/reject takes, select/modify/approve art (needs an art brief: you can
   reuse `uat/rolex/art_brief.json`), build a storyboard. A full render takes ~12 minutes; you may skip rendering your
   own project if you review the first tester's render instead — say which you did.
2. Try to reproduce the defects in `var/uat/defects.log` on the CURRENT code and say whether each fix holds.
3. Look for new functional and usability problems (layout on iPhone width, confusing labels, dead ends, missing
   feedback, states that lie, things that look approved but are not, actions without confirmation).
4. Verify approval states and saved decisions survive a server restart and a page reload.
5. Confirm the paid gateway cannot be triggered from the UI or the API (try).
6. Review the first tester's final draft film: watch frames (extract stills with ffmpeg and look at them), check the
   opening frames move, captions, end card, historical accuracy of what is on screen against
   `research/rolex-oyster.json`, and audio/caption sync (e.g. whisper on the audio vs caption timing).
7. Challenge claims: for every PASS in `var/uat/results.json` you have doubts about, say why. Point out any test that
   cannot fail, any check that is cosmetic, anything labelled as tested that only a mock touched.

## Report

Write `var/audit/AUDIT_REPORT.md` with: what you tested and how; a table of features with your own classification
(PASS / FAIL / PARTIAL / BLOCKED / NOT TESTED) and evidence paths; every defect (severity, steps to reproduce,
expected vs actual); disagreements with the first tester's results; and what you could not test. Keep screenshots
under `var/audit/shots/`. Be specific and blunt.
