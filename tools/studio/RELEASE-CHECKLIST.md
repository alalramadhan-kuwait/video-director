# Release checklist: studio map, rounds 1–12 (plans v1–v11; run by the coordinator, in this order)

Nothing here has been run against the live studio. Every script was dry-run on local copies, and the reports are in this folder.

### 0. The live page carries four hotfixes (v118–v121, 8 Nov); this release keeps them (round 11)
- The live page was patched outside staging (`flowaudit/live-hotfixes.md`; source `livepatch/studio.html`, v121). The release ports them (CHANGES-v10, «Live hotfixes v118–v121»): the carousel's «📷 احفظ الكل بالصور» (a zip of the slides only, for his Shortcut **Save TK Post**) + «انسخ الكابشن», the line «بعد الضغط اختار Save TK Post…», «صورة صورة (اضغط مطوّل)», the four-step how-to with the Shortcut setup, and file names by the real image type.
- Before publishing, open the release build and check those five on a carousel (`tests/v10.mjs` checks them: «hotfix v118…v121»). If the live page has been patched again since v121, diff `livepatch/studio.html` against the newer live source and port that too **before** publishing, or the release undoes it.
- After publishing, ask him to save one approved carousel with Save TK Post on his iPhone (the frame's share sheet and press-and-hold on WebKit were not testable here).
- **v11 (L1), the same device check:**
  - read the `cache-control` of a studio asset once on the real studio: Claude runs `curl -I` on one `/_blob/<id>` through the page's origin at deploy (or he opens one in the browser devtools on his phone), and writes the header into CHANGES-v11 («L1»). It no longer decides the cost of press-and-hold (v11 draws that view from the copies already on screen), but it does decide what a re-open of the studio costs.
  - ask him to press and hold one image in «صورة صورة (اضغط مطوّل)» and confirm iOS offers «Save to Photos». The images are now `blob:` copies (`-webkit-touch-callout: default` kept); if iOS offers no «Save to Photos» on them, tell the coordinator before anything else ships (the fallback is the v10 behaviour, the `/_blob/` address).

### 1. Build the release and run every test
- Run `stage/build.sh --release`. It writes `stage/release/index.html` and `stage/release/studio-workflow-map.html`.
  - It drops the dev-only gaps «Claude للحين ما يعرف …» and the «ما فيه مهمة أسبوعية» notes.
  - It keeps the real gap: no credits figure in `library.json`.
- Start a server on `stage/` (`python3 -m http.server <port>` from `stage/`), then run:
  - `node stage/tests/escape-lint.mjs` (0 unsafe interpolations in the 5 modules **and in the built pages**, dev and release, `base.html` and every splice rep included) and `node stage/tests/escape-lint.mjs --selftest` (35/35);
  - `node stage/tests/xss-sweep.mjs <port> --release` and `node stage/tests/xss-sweep.mjs <port>` (4/4 each: a markup and a CSS payload in every rendered string of the films, ideas, inbox and studio docs, 109 routes and 258 map sheets: nothing runs, no CSS from data, no outside request);
  - `node stage/tests/guard.test.mjs` (31/31; v10: bound to immutable `/_blob/<32 hex>` addresses with no hashing, no no-store or cache-busted fetch, one fetch per address shared as the copy on screen, the final streamed then fetched once, chat approval rows, a retry with its own timer, his own write never cools, hide is one tap, 14 file cases; v9: made_from required, resend by its row, type poison cleaned; every action bound or harmless, one guarded `publishFile()`, the paying-option order, `safeUrl`; v8: every bound kind has a projection, no tap sends `last_action.text`, no question looked up by key alone, the gate compares the kept projection, one two-tap arm, publishing needs the approved file, 9 file cases);
  - `node stage/tests/flowcore.test.mjs` (must be 189/189);
  - **`node stage/tests/plan.mjs <port> --release`: the full suite, on the build that ships** (must be 219/219). Its screenshots go to `shots/v11/` (or `--shots <folder>`); it refuses to write into a folder named after another round, or one that holds another round's screenshots (`tests/shots-guard.mjs`);
  - `node stage/tests/plan.mjs <port>` (the dev build, the same checks; screenshots in `shots/v11/dev/`);
  - v11: `node stage/tests/v11.mjs <port> --release` and dev (11/11 each: the round-11 reviewer's B1, B1b, B2, B2b and B2c, the button after the third try, the separate fetch and player retries, press-and-hold from the copies on screen, the newer approval wins, «هذا الفلم منشور»);
  - v10: `node stage/tests/v10.mjs <port> --release` and dev (40/40 each: assets only, streaming, one fetch per slide, progress, AbortController, 20-slide cap, the final, chat approval, live rolex-ep1, the retry 30×, no self-notice, the notice at the top, one tap except money/publish/delete/purge, `house_ok` by version; round 11: the ported live hotfixes v118–v121: the «📷 احفظ الكل بالصور» row, the Save TK Post line, «صورة صورة (اضغط مطوّل)» kept open across redraws, the four-step how-to, one tap → one zip of the slides only built from the bytes on screen, real-type file names, nothing for non-asset slides); `node stage/tests/flows.mjs <port> --release` and dev (11/11: his normal day, reel and carousel, **zero refusals, one tap to share and to save**); `node stage/tests/iphone/day.mjs 1500` and `… 1500 --frame` (the artifact frame: no Web Share, the zip for Save TK Post) (his day on the iPhone 13 profile at 1.5 Mbps on a real HTTP server; `STAGE_DIR=stage-r9snap` / `stage-r8snap` for the earlier builds; output in `tests/out-r10/`); `node stage/tests/v9.mjs <port> --release` and dev (24/24 each: it still runs and passes; v10 removed only the hashing it once checked); `node stage/tests/poison.mjs <port> --release` (4/4: every field of every live record poisoned, one at a time); `node stage/tests/kit.mjs <port> --release` (15/15: the editor draws what `tools/carousel/carousel.mjs` renders); `node stage/tests/house.mjs <port> --release` and dev (16/16: «فحص قواعد البيت» in its three places, «يتعلم» after every «تعديل», «✓ قواعد البيت» only when `house_ok` is this version);
  - `node stage/tests/v7.mjs <port> --release` and dev (18/18 each: taps bound to what he saw, only the approved final/slides shared, no colour in CSS). It writes **no screenshots unless `--shots [folder]`** is given (default `shots/v11/`), through the same round guard;
  - `node stage/tests/v8.mjs <port> --release` and dev (33/33 each: publishing tied to the file, the live `gleitze` case, a redraw that changes a button, a double tap, «أعد الإرسال», malformed and duplicate questions, the purge/words/hook rows, no approve while comparing). Screenshots only with `--shots`;
  - `node stage/tests/release-smoke.mjs <port>` (5/5);
  - `bash stage/tests/deploy.test.sh` (57/57; v11: the newest live copies give 3 writes and 0 on a re-run, `gphg-prices` done and posted 0 writes, chat rows count, no approval on a non-asset address, `reupload.py` binds the posted films and refuses `gleitze`, and the release page on the re-uploaded `halter-1`, `halter-2`, `halter-1-carousel` shows what live v121 shows (`tests/reupload-view.mjs`, its own server, stopped by PID); v10: approved_src/approved_slides, media_fix listed on the live copies, flow-migrate `--prev`; backfill, check-version, purge-plan, flow-migrate on local copies; v8: the backfill on the live copies, the exact-path purge).

### 2. Repo sync first (L8)
- Copy the staging sources into the repo's studio-page folder (`flow-seed.json` included) by PR, **before the rules step**, so the rules' pointer to the build is true from the moment they are live.
- Until the page is published, the rules read the locked steps from the published page's `FLOW_LOCKS` (§0); the repo copy is the same build.

### 3. Apply the rules
- Merge `stage/rules-draft.md` into `vd-next` `skills/reel-master/references/studio.md` (and `.claude/skills/…`) by PR, merged when green.
- The release map says Claude knows these rows, so the rules must be live before the page.

### 4. Read the live shapes, read-only (M5)
- Read the live `films/idea-reel-mw6tw5wl.words_check.items` once more. On 7 Nov it had 28 items (word, line, kind) and **no options**. The page now accepts options as plain strings or `{name, hint, audio}`, so either shape is safe.

### 5. Backfill `approved_version` and `approved_file` before the page goes live, and again right after it
1. Read the live `films` and `inbox`.
2. Run:

   ```
   python3 stage/deploy/backfill.py --films <films dir> --inbox <inbox dir> --out <dir>
   ```

3. Check `backfill-report.md`, then apply `backfill-batch.json`:
   - there is **one op per film**, an `update` of `films/<id>` with whole top-level values (no dotted keys): `voice` is the record's own voice with `take_id` added, and a waiting film gets a real `changes` line `{at, v, what}` in front of its own list;
   - **before each write, re-read the record, save it, and run `python3 stage/deploy/check-version.py <record.json> <if_version>`.** On «changed», skip it and re-run the backfill.
4. **Run it again right after the publish (step 8),** in the same session.
   - v9: run it **with `--media <dir>`** holding local copies of every `video` and `final` a film that is not posted names (download them read-only first). Then a bare final that is not the video itself is compared by length and, within 0.3 s, marked with `final_version` and `final_from` (flagged «تأكد»; v10: no `final_hash`); otherwise it is listed `final_needed`: prepare it (rules §6) before he saves. Without `--media`, `rolex-ep3` stays unmarked and his save writes a `final_needed` row. It is idempotent: 0 writes on its own output after a shallow or a deep merge (`tests/deploy.test.sh`). The second run catches any film approved on the old page between steps 5 and 8.
5. Check the report's ⚠ lines by hand:
   - a posted film updated after it was posted (`halter-1-carousel`);
   - a posted version that is not the last finished approval (`gleitze`: approved v5, posted v8);
   - v8: a posted film whose `final` is not shown to be for the posted version gets **no** `approved_version` (`gleitze`: `final` is `film/gleitze-v5-full.mp4` under v8; `rolex-ep2`: changed after the post). Before anyone saves it again, upload the posted version's final as `{url, version, made_from}` and have him approve it;
   - v11 (S24): a film whose media are not studio assets is listed «media_fix بس» and **nothing about its approval or state is written** (never an approval naming a `film/…` or `carousel/…` path). Its approval comes with its re-upload (step 6);
   - v11 (S23): a record that already carries his approval (`approved_version` = `version`, `approved_slides` / `approved_src` = what he sees, whatever `approved_file` holds) is left alone: «موافقة مكتوبة بالسجل» (`gphg-prices`, `gphg-carousel-mw70ulvs`). An S19 chat row (`via: 'chat'`, `approved_src` / `approved_slides`) counts as his named approval;
   - v8: a `done` film whose approve row does not name its current file goes back to waiting (`dennison` on the live copies), so he approves the file himself.

6. **Re-upload every file the report lists as `media_fix` as a studio asset, before the page goes live, finals included (v11: with `reupload.py`, which binds the posted films in the same write).**
   1. On the live copies these are: `halter-1` (`film/halter-1-v19.mp4`), `halter-2` (`film/halter-2-v7-full.mp4`, its video and final), `halter-1-carousel`, `jewels-carousel`, `rubies-carousel`, `rubies-carousel-simple` (`carousel/…` slides), `rubies`, `rubies-engraving`, `tenten` (`film/…` videos), and `gleitze` (`film/gleitze-v5-full.mp4`, see 4).
   2. Upload each file as a new studio asset (a new `/_blob/<id>`) and write a map `{"<old path>": "/_blob/<new id>", …}`. **For a posted film, upload the file that was posted** (it is: the posted version's own file at that path; `halter-1-carousel` was updated 7 s after its post, by the post itself: check the slides are the posted ones). Re-uploading the posted file gives the posted bytes.
   3. Run `python3 stage/deploy/reupload.py --films <films as read now> --map <map.json> --inbox <inbox dir> --out <dir>` (a dry run: it only writes `reupload-batch.json` and a report). One `update` per film: the new `video` / `slides` / `final` (`{url, version, made_from}`) and `media_at`; **for a posted film, in the same write, its approval at the new addresses**: `approved_version` = the posted version, `approved_src` / `approved_slides` and `approved_file` = the new addresses, `approved_via: 'reupload'`. An open film gets the addresses only; he approves them on the page. A film with a path the map lacks, or a map value that is not `/_blob/<32 hex>`, is refused and listed.
   4. **`gleitze` is refused on purpose:** posted v8, its `final` is the v5 file. Leave it until the posted v8's own final exists (open items below); meanwhile the page says «هذا الفلم منشور» there and writes no row.
   5. Apply the ops as in step 3 (re-read, `check-version.py`, skip on «changed»), then re-run `backfill.py`: 0 writes for these films (they now carry `approved_file`), and `reupload.py` on the result: 0 writes.
   - Dry run on the newest copies (`tests/out-v11/backfill/`, round 12): 9 writes (`halter-1`, `halter-2`, `halter-1-carousel` bound; six open films re-addressed), `gleitze` refused; re-runs of both scripts 0 writes; on the release page the three posted films then show what live v121 shows («انسخ الكابشن» and «احفظه ملف» on `halter-2`; «📷 احفظ الكل بالصور», «انسخ الكابشن» and «صورة صورة» on `halter-1-carousel`; `halter-1` has no caption, as on live).
7. **v11 (L2): re-check the house rules for every open film** (rules §10, `tools/house_check.py`) and write `house_ok: '<its version>'` for each that passes, in the same session as the publish. An old `house_ok: true` (`spaceone-baltic-gphg`, `gphg-prices`, `gphg-carousel-mw70ulvs` on the live copies) shows no «✓ قواعد البيت» on the new page.

History (superseded by the round-12 run below): The dry runs (v8): `stage/deploy/backfill-dryrun/` (the older `db/films` copies) writes 6 records; `stage/deploy/backfill-dryrun-live/` (the read-only live copies of 8 Nov) writes 6: `halter-1`, `halter-2`, `rolex-ep1` and `halter-1-carousel` (posted), `dennison` (back to waiting, with its `voice`) and `rolex-ep2` (`voice` only). `gleitze` and `rolex-ep2` get ⚠ and no `approved_version`. A re-run on the applied result writes nothing.

History (superseded by the round-12 run below): Round 11 re-ran both (8 Nov, after the live hotfixes): `backfill-dryrun-live/` (the 01:14 copies, 18 films) still writes 6 (`dennison`, `halter-1-carousel`, `halter-1`, `halter-2`, `rolex-ep1`, `rolex-ep2`). The newest copies, `backfill-dryrun-live-1423/` (`hourly/1423`, 20 films, the same inbox copy), write 8: the 6 kinds above plus `gphg-carousel-mw70ulvs` (posted v10, approved from its «نشرت» row) and **`gphg-prices` back to waiting** (done v2 with `approved_version: 'v2'` from the live page, but no approve row naming its slides in the inbox copy: he taps «موافق» once on the new page). (Corrected in round 12: a fresh inbox could not have changed that; the v10 backfill ignored a record-level approval and the live page's row names no file.) `dennison` is now posted (its approval comes from the record). `media_fix`: the same 10 films as above.

Round 12 (v11), the newest copies (`hourly/1423` + `chk2016/films`, inbox `flowaudit/db/inbox` + `chk2016/inbox`, 35 rows): **3 writes** (`dennison` and `rolex-ep1` approvals at their `/_blob/` videos, `rolex-ep2` voice only); `gphg-prices` and `gphg-carousel-mw70ulvs` 0 (approved on the record); the posted films with `film/…` / `carousel/…` media 0 (bound at step 6); no op writes `state`, `waiting` or a `changes` line; re-runs after a shallow and a deep merge: 0 writes.

### 6. Migrate an existing applied map, after his yes (M3)
1. If `studio/flow` exists, read it and run:

   ```
   node stage/deploy/flow-migrate.js <it>.json stage/release <round-0 seed> <dir> --prev <the live page's build: a folder with its flowcore.js and flow-seed.json>
   ```

   v10 changed the locked review and save steps' text, so a map saved under the live page differs from this release's locks by exactly that. With `--prev`, a map whose locked parts are exactly the live page's is kept: its locked steps, and every step he never edited, become this release's; his own edits stay. A map that changed the locked parts under the live page too is refused whole, as before. Without `--prev` (or if unsure which build is live) the map is refused whole and his edits are listed for him, as before.

2. Show him the report's dropped edits in one message (removed buttons included). The script refuses to write a result the page itself would refuse (exit 3), and never carries the old doc's own text or version into the result: the old map goes into history with a number, a date and a neutral note.
3. **Only after his yes**, write `studio-flow.migrated.json` to `studio/flow`, and mark every unhandled `inbox/flow_lock-<applied_at or x>-<content hash>` row handled (while any is unhandled, Claude follows the built-in map).
4. If there is no `studio/flow`, nothing to do. If he says no, leave `studio/flow` as it is: the page keeps using the built-in map.

Dry runs (`deploy/migrate-out/`): none, old (pre-lock), honest (kept), tampered, the reviewer's crafted `base_acts` map and a null-edge map (all three refused whole).

### 6b. The carousel editor's font (v9, the owner's identity of 8 Nov 2026)
- Upload `vd-next/brand/carousel/Bahij-Helvetica-Neue-Bold.ttf` and `…-Roman.ttf` to the studio artifact's assets, and write `studio/brand` `{font_bold: '/_blob/<id>', font_roman: '/_blob/<id>'}`. Only `/_blob/<id>` values are used.
- Until it is there, the editor draws with the kit's Tajawal (or the system font). The layout follows `tools/carousel/carousel.mjs` either way: TK green, the number in a black box, «▶▶ اسحب للمزيد» on the cover, `news`/`big`.

### 7. Create the weekly scheduled task
- Use the prompt in `stage/deploy/weekly-task.md`. It asks by id on `studio/purge` and uses `stage/deploy/purge-plan.py`:
  - `deploy/purge-dryrun/`: duplicate names, a hidden «done» film, a yes for a subset, a forged id, a film hidden after the question;
  - `deploy/purge-dryrun-r5/` (the reviewer's set): a film hidden 1 minute before the question is kept (30-day rule), a file another film uses is kept, a film he kept is not asked again for 30 days.
  - v8 (M5): the delete list holds exact paths only, and the prompt deletes exactly that list, one by one. On the live copies, purging `rubies` lists `film/rubies-v11.mp4` and `posters/rubies.jpg` only (never `rubies-engraving` or `carousel/rubies/`), and purging `halter-1` never touches `carousel/halter-1/` (`tests/deploy.test.sh`).
- Schedule it once a week, Kuwait time, outside 6–9 AM Pacific.

### 8. Publish (then re-run step 5)
- Publish `stage/release/index.html` to the studio artifact, with the owner's approval as always.
- Publish `stage/release/studio-workflow-map.html` to the standalone map.

**Every approved film needs its `final` (1080×1920) uploaded, marked for its version:** «احفظ الفيلم» shares a `final` only when it is `{url, version, made_from}` (or carries `final_version`) for the approved version and was made from the video he approved; otherwise the button stays off with «الملف النهائي مو للنسخة اللي وافقت عليها، Claude يجهّزه». The light `video` is never shared.

**Keep step 5 before step 8.** Until the backfill runs, a film with no `approved_file` cannot be saved or shared at all (v8): every approval must name the file.

### 9. Verify live, read-only
- Open the studio and check that:
  - after the re-upload (§5 step 6), the posted `halter-2` shows «انسخ الكابشن» and «احفظه ملف», `halter-1-carousel` shows «📷 احفظ الكل بالصور», «انسخ الكابشن» and «صورة صورة», and `halter-1` (no caption) shows what it shows on live; none says «نسخة مو معتمدة للحين». `gleitze` says «هذا الفلم منشور» and shows no «انسخ» until its v8 final is uploaded (open items);
  - `gphg-prices` still shows «📷 احفظ الكل بالصور» and «انسخ الكابشن» (approved on the live page; the backfill wrote nothing for it);
  - the open films show «✓ قواعد البيت» only where step 7 wrote `house_ok` for their version;
  - a waiting film shows «نسخة مو معتمدة للحين» on its publish page;
  - `#flow` shows 1 gap per kind and no errors, and «نسخة 5» in its note;
  - a locked step's sheet shows 🔒, «توافق على البناء؟» included;
  - opening the studio twice adds no `flow_lock` row.

### Open items (not done by this release)
- **`gleitze`** (posted v8): its `final` is `film/gleitze-v5-full.mp4`, the v5 file. Claude prepares the posted v8's own final, uploads it as an asset with `{url, version: 'v8', made_from}`, and runs `reupload.py` for it; until then the page says «هذا الفلم منشور» on it, with no «انسخ» and no save (live v121 shows «انسخ» and «احفظه ملف» there).
- **`rolex-ep2`** (posted, changed after the post): no approval written; Claude checks which file was posted before binding it.

