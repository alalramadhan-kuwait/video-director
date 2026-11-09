# The studio: the owner's dashboard (theme A)

https://claude.ai/artifact/UQ2iS18beg8zt9DztSLNZ6 — the owner follows every film here from the iPhone: its percentage,
the time left, and what waits for them (the owner, 2 Nov 2026: «i want to see % and timing to finishing and wait for
action if applicable»). Its look is the owner's pick, theme A, the celebration dial: cream ground, one bright colour
per film, rounded cards, a dark floating tab bar, little text.

The page's source is `studio-page/` in this repo (index.html, library.json); its media (film/, posters/, samples/,
carousel/, the old studio's panel/ avatars) are published files of the page only, never in git (the repo is public).
Several sessions publish it: before publishing, read the live page (Artifact `read`) and build on it, then copy the
result back into `studio-page/` in the same change. One version of the page holds at most 256 MB: drop superseded
drafts no record points to (`null` in `files`) before adding new media. Its records live in its database, never in
its source; write them with the ArtifactData tool (`url` above).

A carousel's working folder (spec.json, caption.txt, its cut-outs and cover; credited press photos included) is kept
on the page too, under `src/carousel/<id>/`, so any later session can change one slide and render it again; the
scratch folder of the session that made it does not outlive that session.

## Keep it current: at every step of SKILL.md
Write `films/<film id>` when a step starts, when it ends, and when a gate waits for the owner. Fields:

| field | what |
|---|---|
| `name`, `title` | the card's short name, the film's title |
| `order`, `color` | position on the list; one of #2BB5B8 #F2765F #E9A0C0 #A8D8A0 #F2C230 |
| `step` | 1–9, SKILL.md's steps: idea and research, hook and script, readers, voice, pace, style, pictures and build, review, delivery |
| `state` | `working` (Claude on it), `waiting` (a gate for the owner), `done`, `posted` (the owner pressed «تم النشر ✓») |
| `now` | while working: what is happening, in a few words («أسجّل الفصل الثاني») |
| `eta_min` | while working: minutes left, from what the step usually takes (voice ~1 min a section, stills ~3, full render ~8–12, critic round ~10) |
| `waiting` | while waiting: what the owner decides («موافقتك على السكربت») |
| `after_min` | while waiting: minutes to finish once they decide |
| `version`, `seconds`, `versions` | the latest version, its length, the version list newest first |
| `updated`, `changes` | **with every new version** (the owner: «شلون اعرف اذا هذي اخر نسخة تم تحديثها متى؟ وشنو كانت اخر التغيرات؟»): `updated` the time (ISO, UTC) and `changes` `[{v, at, what: [one short line per change, in the owner's words]}]`, newest first, at most 20. The film page shows «آخر تحديث» in Kuwait time with its age and the latest changes, the older ones folded; the cards show the version and its age. The studio's own text editor writes its entry itself |
| `video`, `poster` | a published file of the page: a light copy of the film (720 px, crf ~29, under 15 MB) and its cover |
| `caption`, `music`, `credits`, `sources` (a film) | **with every version the owner reviews**, not only on approval (7 Nov 2026 audit, gaps G2 and G4: the owner reviews the caption with the film, and a CC BY music credit must never live only in a local file): `caption` in the house style (below), `music {name, by, licence, url}`, `credits [one line each]`, `sources [{title, url?}]`. The review and publish views show them |
| `built_from` | with every video version: `{script: 'نص v4', voice: 'صوت v5'}`, so the owner sees which script and take are inside it (G11) |
| `voice` | with every take: `{audio, chars, lines: [{n, text, from, to}], words: [{line, word, options: [{name, hint, audio}]}]}`. `audio` is the whole take as audio-only AAC `.mp4` (the store refuses mp3), `lines` the on-screen text with the take's times, `chars` **the billed ElevenLabs count of that take (emotion tags included)**: the page's re-record cost comes from it and never from the on-screen text, which read about 40 % low (G3). `words` holds the spoken options when the owner marks a word (`kuwaiti-voice.md`): the studio voice view is the one place he picks them (G6) |
| `prev_video`, `prev_version` | while a version waits for the owner: a light copy (720 px) of the version before it, for «قارن مع النسخة اللي قبل» (G5). Deleted with the owner's approval (the one exception to «One copy only») |
| `checks` | with every version: `[{who, round, found, fixed}]` from the readers, the critic, the sound check and the collector check, shown as «وش صلّح الفريق» (G12) |
| `cost` | per film, kept current after every paid call: `{elevenlabs_chars, higgsfield_credits, note}`. `studio/costs` holds the balances `{at, elevenlabs: {used, limit, resets}, higgsfield: {balance, plan}}`, refreshed after every paid call (ElevenLabs `/v1/user/subscription`, Higgsfield `balance`) (G13) |
| `asks` | several open questions on one film at once: `[{key, q, options}]`, each shown as buttons in «دورك الحين»; a tap adds an `inbox` row `{kind: 'answer', key, answer}`. Use it for side decisions such as a title, and once a week for every film waiting over 3 days («كمّله / خلّه على جنب / احذفه») (G10, G14) |
| `final`, `caption` (a film) | **ready before the owner approves; written at once on approval at the latest** (the owner: «مفروض بعد الموافقه يعطيني الفيديو جاهز للحفظ مع الكابشن»): the film at full size (1080×1920, two-pass to under 16 MB, a published file's limit) and its post caption (hook, the story in two lines, the reader's question; never hashtags or sources, the owner 8 Nov 2026). An approved film shows «احفظ الفيلم ↗» (the share sheet's Save Video; the caption goes to the clipboard on the same tap) and its caption |
| `acts` | `[{name, time}]` once the voice exists |
| `meta` | type · language · look · voice |
| `done_text` | when done («جاهز للنشر», «منشور») |
| `posted` | `{at, version}`, written by the page's «تم النشر ✓»; the reads fall due 48 h and 7 days after `at` |
| `approved_version`, `approved_src` / `approved_slides`, `approved_file`, `approved_at`, `approved_duration`, `approved_via` | written by the page's «موافق» **only when he approves the finished film or carousel** (v7: and only when the version and the files on his screen are the record's): the review of a film with its video (stage «المراجعة»), or a carousel with its slides. **v10: the approval names the exact studio asset addresses he saw**: `approved_src` = the `video` he watched (never the final), or `approved_slides` = the slide list (`approved_file` holds the same, for older readers); `approved_duration` = the video's length from his player; `approved_via: 'page'`. Studio asset ids are immutable (every upload gets a new `/_blob/<32 hex>` id and nothing overwrites one), so the same address is the same bytes. **The page lets him save, copy, share or mark posted only when `state` is `done` or `posted`, `approved_version === version`, and the approved addresses are the very `video`/`slides` now.** For a carousel, a pending «موافق» on that same version and slides also counts. **When he approves the finished piece in chat (v10, a first-class path):** write `approved_version`, `approved_src` (a reel) or `approved_slides` (a carousel) = exactly the addresses he saw, `approved_file` = the same, `approved_at` = now, `approved_via: 'chat'`, and for a reel `approved_duration` (its length in seconds, from ffprobe), with `state: 'done'`; and add one inbox row `{kind: 'approve', via: 'chat', film, version, approved_src | approved_slides, at}`. The page accepts either exactly like his tap while the addresses still match the record (v11: when both name this version, the newer of his tap's `approved_at` and the chat row's `at` wins). **At deploy only (v11), a posted film re-uploaded as assets** gets the same fields for its new addresses in the re-upload's own write, with `approved_version` = the posted version and `approved_via: 'reupload'` («v11: re-uploads, posted films and the deploy»). Never write them for anything else. |
| `media_at` | Claude stamps it (ISO time) in the same write as every change to what he watches: `video`, `slides`. v10: it is a record of when, not the binding: a new cut is always a new address (a new upload), so a moved `media_at` on the same address does not void his yes. |
| `final` | **`{url, version, made_from}`**: the full-quality file (a studio asset), the version it is for, and the `video` it was made from (= his `approved_src`). Or a plain URL with `final_version` (and `final_from`) beside it. **The page shares a final when it IS the file he approved** (the live shape: `final === video`, an asset), or when `final.version === approved_version === version`, `made_from` is his `approved_src`, and its length (from its own player's metadata) is within 0.3 s of `approved_duration`. Otherwise «احفظ الفيلم» stays off with «الملف النهائي مو للنسخة اللي وافقت عليها، Claude يجهّزه». |
| v10: studio assets only; `saved_src`, `final_needed`, `media_fix` | **Every file he approves, shares or saves is a studio asset, `/_blob/<32 hex>`** (`video`, `final`, `slides[]`, `voice.audio`). **Always upload media as assets (a new id every time); never re-use or overwrite an address, and never point a record at a published `film/…` or `carousel/…` path or an http URL.** Any other address gets no «موافق» and no «احفظ/شارك»; the page shows «Claude يرفع الملف من يديد» and writes one `media_fix` row. The page hashes nothing (v9's `approved_hashes`, `final.hash` and `saved_hash` are gone): a video streams from its address; a slide is fetched once by its address and shared as the copy on screen; «احفظ الفيلم» plays or scrubs the final in its own player, turns on once it drew a frame and its length matches, then fetches it once from the same address for the share sheet. The save writes `saved_src` (the final's address) on the record and a `saved` row; «تم النشر» carries it. When a save is off for a marking reason the page writes one `final_needed` row `{film, version, final, why}` per film and version (never for a posted film). A carousel shows at most 20 slides (Instagram's limit): more renders the first 20 with «فيه شرائح زيادة», no «موافق», and a `media_fix` row (`why: too_many`). |
| `house_ok` | **Claude writes `house_ok: '<the version it checked>'` (v10: the version string, e.g. `'نص v3'`) only after the house rules gate passes** for the text the owner is about to see (video-director #189: `brand/house_rules.yaml`, `tools/house_check.py`): the script before its card, the carousel (spec and caption) before it renders, the caption before it is saved. The studio shows «✓ قواعد البيت» only when `house_ok` equals the `version` on screen, so a new version is unticked until Claude checks it (an old `true` shows nothing). The page cannot run the check; the code gate is in the repo: `record_flow` refuses a paid take and `make.py` refuses to render while a rule is broken (`--rules-ok` only with the owner's word). |
| `step_approved` | written by «موافق» on a step (script, voice, sample): the version he approved at that step. It never unlocks publishing. Move the film to its next step. |
| `voice.take_id` | **set on every full take** (a new id per whole take, kept unchanged through line fixes and splices). The word-fix count follows it. Without it the page falls back to `voice.takes`, and never to the audio file, which changes with every line fix. The deploy backfill sets it once from the current audio file. A yes to `voice_cost:full` also starts the count again. |
| `fix_rounds` | written by the page: `{take, words: {<word>: n}}`, the pronunciation fixes sent per word for the take `take` (= `voice.take_id`, or `voice.takes`). A new full take (a new `take_id`) starts every word at 0 again. At 2 for a word (`n_relines.max_rounds`), the page stops offering that word and shows «الكلمة ما ضبطت؟ نغيّرها» instead. |
| `last_action.resends`, `flow.resends` | written by the page: how many times «أعد الإرسال» was used. After 2 (`max_resends`) it shows «قل لي بالمحادثة» instead of the button. |
| `flow.rounds` | written by the page: `{dir, style}`, the «ما عجبني شي» rounds in words. It is kept on `flow`, outside `more`, so a pick in between does not reset it. Keep it when you rewrite `flow`. After `max_rounds` (3, on the map's «تكتب شنو تبي» steps) the page offers no 4th round. |
| `insights_shots` / `insights_sent` | the owner's uploaded screenshots `[{stage, at, shots}]` / the reads he has sent (`48h`, `7d`) |
| `insights` | Claude's reads `[{stage, at, verdict: good|mid|bad, label, vs, numbers: {name: value}, lessons, next}]` (`references/insights.md`) |
| `kind` | `carousel` for a carousel (a Reel leaves it out) |
| `slides` | a carousel's PNGs in order, as published files (`carousel/<id>/01.png` …) |
| `caption` | the post caption; «شارك الكل» saves one zip of every slide and the caption (the Claude app allows one file per prompt, and its share sheet one file) and copies the caption; the numbers under it save one slide each |
| `of` | the record of the same topic in the other format (a carousel's Reel, a Reel's carousel). The page links the two, or offers «سوّ منه كاروسيل/ريل». «الاثنين» (in «فكرة جديدة», «ريل عجبك» or «ابدأ بهالنوع») creates both at once: the Reel, then the carousel with `of: <reel id>`. Each gets its own request row: the Reel's has `format: 'both', twin: <carousel id>`, the carousel's has `of: <reel id>`. Handle both, and mark both «استلمت». |
| `spec`, `src` | a carousel's spec.json (its texts, layouts, pictures) and the published folder of its pictures (`src/carousel/<id>/`): with them the owner edits the text in the studio himself (below) |
| `topic` | **every record** (the owner: «group the topics together, because some are the same topic»): the topic's id (`rubies`, `halter`, `tenten`); the list shows one card per topic, its Reels and carousels as slim rows (kind, version, when it was made in Kuwait time, rules). `studio/topics` names it: `{<id>: {name, color}}`; a new topic gets its entry there |
| `rules` | **with every new version** (the owner: «so I can know the new rules are applied to this or no»): the ids of the newest rules this version follows (the page's `RULES`, or `studio/rules` `{list: [{id, kind: reel|carousel, at, name}]}` when set). Without it a version made after a rule's `at` counts as following it, so write it whenever that would be wrong (a re-render of old work). A new permanent rule goes into `RULES` (and `studio/rules`) with the time it became law, so older versions show «⚠ قبل … قواعد جديدة» |
| `history`, `edited` | the last 10 versions before an edit in the studio, **text only**: `{version, spec, caption, at}`. Old slide files are never kept. After a save or an undo, the page deletes the `/_blob/` slides it replaced, except any that an unhandled `inbox` row still points to. Published `carousel/<id>/…` files stay until your next publish of that carousel, which removes them («One copy only»). «رجّع النسخة السابقة» redraws every slide from the old text with the same base (`src`). An edit or an undo sets `state: 'waiting'` and `waiting: 'موافقتك على الكاروسيل'`, so nothing edited can be published before his yes. A posted carousel cannot be edited in the studio. `edited: studio` once he has changed it there. |

The percentage is the share of steps done (step − 1 of 9; 100 when done). `studio/now` holds the line at the top:
`{busy, text, at}` (hidden once it is over 3 hours old and Claude is not busy: keep it current).

Money questions use a key that names what they price:

| Key | What it prices |
|---|---|
| `voice_cost:full` | a whole take |
| `voice_cost:opt` | three spoken options |
| `voice_cost:lines` | re-recorded lines |
| `ai_cost:sample` | an idea-stage sample |
| `ai_cost:style` | a style-stage sample |
| `ai_cost` | AI clips |
| `ai_cost:car` | a carousel's AI images |

Put the estimate in the question («حوالي 140 حرف», «حوالي 120 رصيد») or in `cost`.

**v8: one key, one question.** Every item in `asks` has a plain-text `key` (no line breaks or other control characters) that no other open question on that film uses. Two questions with the same key, or a key that is not plain text, show disabled on the page («سؤال مكرر، Claude يصلحه» / «سؤال ناقص، Claude يصلحه») and cannot be answered: fix the record. The page binds every option to the question's position and full text (`key`, `q`, `options`, the price), so a question rewritten under his first tap is refused.

Options are plain text, or `{t, pays}`. **Every option that spends needs his second tap** («اضغط مرة ثانية: يصرف …», with the option's own amount if it names one). The page decides in this order, and **a «no» is a whole answer, never a prefix**:
1. An option that names a spend («سجّل», «تسجيل», «التسجيلة», «رصيد», «حرف», «توليد», «يولّد», «ذكاء»/«اصطناعي», «دفع», «كريدت», «AI», «سوّها بال…», «credit») or an amount («140 حرف», «120 رصيد») is two taps.
2. An explicit `pays: true` is two taps.
3. On a `voice_cost*` or `ai_cost*` question, **every option that is not exactly a no is two taps**: so «خلاص، كمّل», «لا بأس، كمّل», «لا مانع» and «بديل ببلاش» all ask twice there.
4. Exactly a no is one tap. The no set, after removing marks and punctuation: «لا», «مو الحين», «لا شكراً», «خلها», «خله», «خلها على جنب», «بعدين», «لاحقاً», «no», «no thanks», «not now», «later».
5. `pays: false` comes last: it never makes an option with a spend word, an amount, or on a price key one tap.

So on a price question write the refusal as exactly «مو الحين» or «لا», and give each paying option its own amount: `['اي، سجّل كامل (2,900 حرف)', 'سجّل الجملتين بس (140 حرف)', 'مو الحين']`. A free alternative belongs in its own question without a price key.

**Word options** (`words_check.items[].options`) are plain text (`'وَاللّه'`) or `{name, hint?, audio?}`. Both show and send the same way.

## What the owner sends back
The film page's buttons (approve, change with a note) and the library's «ابدأ فلم بهالنوع» send a comment to Claude
when the platform allows it, and always add a document to `inbox` (`{film, kind, step, note, text, sent, at}`). On a
carousel the change box shows the slides to pick (one or more); the message names them («الغلاف، الشريحة 3») and the
inbox document carries their files in `slides`. On
«شيّك الاستوديو», or when a film waits, read `inbox` and act on what is new.

**Every inbox row is marked when it is handled** (7 Nov 2026 audit, gap G1: the 04:45 ep2 hook pick reached only the
inbox, and nobody could tell which rows were done): `handled_at`, `handled_by: 'claude'`, a short `handled_note`. A row
without `handled_at` is new. **Handling a row also bumps the film's `updated`** (with a `changes` line saying what
was done): the page treats a film whose `last_action.at` is newer than `updated` as still waiting for Claude, and
hides the voice marks and word options meanwhile. On 7 Nov 2026 the Dennison «ليش / الساعة» options were ready but
hidden for this reason, and the owner had to send his marks twice. A scheduled task checks the studio every hour (unhandled rows, and films whose
`last_action.at` is newer than `updated`), acts on them under the usual gates, and writes `studio/now.checked_at`; the
page shows «آخر مرة شيّك Claude». **A decision the owner makes in chat is written to the inbox too** (`via: 'chat'`,
his words quoted, `handled_at` set) and as a `changes` line, so the studio's history shows who approved what (G7).
When a film moves to `waiting`, also tell the owner in one short chat line (G15).

- **What «احفظ الفيلم» and «📷 احفظ الكل بالصور» (the carousel's button, called «شارك الكل» before the live hotfix v121) send (v7, v8, v10).** Only the approved version **and the approved files**: `approved_version === version`, and `approved_src`/`approved_slides` are the very `video` (or slides) on the record now, at the same studio asset addresses. For a film, only its full-quality `final` (1080×1920), and only a final marked for that version (`final.version` or `final_version`) and made from that video (`final.made_from`). The light `video` is never offered for publishing, and the button waits («النسخة الكاملة توصل مع موافقتك», or «الملف النهائي مو للنسخة اللي وافقت عليها، Claude يجهّزه») until such a `final` is there. v10: the page keeps each file by its asset address only (an address never changes its bytes), so after his own edit only the changed slides download. Upload `final` for every approved film.

- **Name versions by step**, so the page can tell the finished piece:
  - `نص vN` (script), `صوت vN` (voice), `رسومات vN` / `أسلوب vN` (style), `تجربة vN` (a sample) are **steps**;
  - only `فيديو vN` (or an old bare `vN`) is the finished film;
  - a carousel's version with its slides is the finished carousel.

- **A new version waits for his yes.** When you upload a new **version** (a new `version` string) of something he can see, set `state: 'waiting'` and `waiting` in the same write. Leave `approved_version` as it was.
- **v8: every new `video` or `slides` stamps `media_at`, and clears or replaces `final` in the same write.** A `final` left from an earlier version is never kept beside a new video. Write each final as `{url, version, made_from}` (or `final` + `final_version`), never a bare URL. Never overwrite a file in place under the same address: a new cut is a new file. Never reuse a version string for a new cut.
- **v9/v10: how to deliver a final, every time.** A new studio asset (a new `/_blob/` upload; v10: never a published `film/…` path); never overwrite an address and never re-use one for other bytes («لا تعيد استخدام نفس العنوان»); write all the marks in the same write: `final: {url, version, made_from: <his approved_src>}`. If the final IS the video he approved, `final: <that same address>` is enough. A final with no `made_from` is refused. After his finished «موافق» («Inbox kinds the page writes»), check `final`: if it is bare, mark it or rebuild it. Carousel slides follow the same rule: a new version is new assets, and only the changed slides get new addresses.
- **The `final` of an already-approved version does not re-lock it.** Uploading the 1080 file after he approved that same version keeps `state: 'done'` and the same `version`, and does **not** stamp `media_at`: write it as `{url, version: <that version>, made_from: <his approved_file>}`.
- **The page keeps it safe if you forget.** A `done` record whose `version` is not `approved_version` shows «نسخة يديدة تنتظر موافقتك» and «موافق على هالنسخة». Nothing saves until he approves it.
- **Step approvals.** «موافق» on the script, the voice or a sample is a step approval (`finished: false`). Move on, and never set `done` for it.

The one-time backfill is a deploy step, not a rule: `tools/studio/backfill.py`, run before the page goes live (`tools/studio/RELEASE-CHECKLIST.md`).

### Inbox kinds the page writes

Every row has `{film?, kind, text, sent, at}` and is marked `handled_at` when done, as above.

| `kind` | written by | what to do |
|---|---|---|
| `request` | «فكرة جديدة», «ريل عجبك», «ابدأ», «سوّ منه…», «جرّبها» | Start it (see «Ideas»). `format: 'both'` with `twin` means two records, each with its own row. `mode: 'sample'` is a style test: go straight to the sample. |
| `flow` | a direction pick, «ما عجبني شي» (a style: `more.name`; a narrative type: `more.type`; his words: `more.text` + `rounds`), «أعد الإرسال» on a request | Follow the request flow in `library.json`. A paid pick has already had his second tap. Still ask the price before you generate anything. |
| `approve` | «موافق» | It carries `version` and `finished`. **`finished: true`** (the finished film or carousel): write `state: 'done'`. The page has already written `approved_version`. **`finished: false`** (a step): move to the next step and do **not** set `done`. **A row with no `finished` field came from the old page:** judge it by its step text («(المراجعة)»/«(التسليم)» = the finished piece). If it is, write `state: 'done'` **and** `approved_version` yourself. |
| `change` | «أرسل التعديل», «أرسل التعديلات», «أرسل الملاحظات» | Apply it in the step the film is at, under that step's price and approval gates. Never go straight to a build. |
| `change` with `say_fix` | «أرسل العلامات» | Word marks. **They are not a yes to spend.** Ask the price first: `voice_cost:opt` (three spoken options) or `voice_cost:lines` (re-record the changed lines). |
| `word_swap` | «غيّر الكلمة بالنص» | The listed `words` did not come out right after 2 fixes. Change them in the script for an easier word. That is a script edit: readers on the changed lines, `script-edits.md`. Send him the script, and record no 3rd fix. |
| `answer` | a question's button | `key` is the question's key. A yes to a priced question arrives only after his 2nd tap; the page always asks twice on **every option that spends** (the price keys, after the film record table), whatever the map says. `later` means ask that same question again later. **`key: 'purge'`** comes only from the home page's purge card and carries `ids`, `asked` (the ids the card showed) and `asked_at` (see «Every «no» has a written path»). A purge `yes` with no `ids`, or empty `ids`, is **not** an answer: the card stays open; never delete on it. Never put a `purge` question in a film's `asks`: the page does not show one there. |
| `words` | «تأكد من الكلمات» | `{cleared, fixes}`. Add the fixes to the word book the same day, and list the cleared words under `kw_ok`. `fixes[].how` is the option he picked or the text he wrote. |
| `missing` | «عندي صورة» / «استخدم بديل» / «شيل اللقطة» | `{id, image?, choice?}`. Use the image, a free alternative, or drop the shot. |
| `suggestion` | «سوّها» on a forecast suggestion | Make a new version with it, for his approval. |
| `insights` | «أرسلت صور الإحصائيات» | Read the screenshots he sent in chat (`references/insights.md`). |
| `resend` | «أعد الإرسال» on a pending action | The row repeats `text`: v8, always the text of the page's own row for that very action (v9: `last_action.row_at` names it; never a neighbour by time) (shown to him in the box before he taps, and carried as `seen_text`), never `last_action.text`. Handle the original action once, not twice. **If `text` is not the text of an earlier row for that film, do nothing with it and ask him.** |
| `final_needed` | the page, when «احفظ الفيلم» is off because the final is not marked for his yes, made from another file, or of another length (never for a posted film) | **Prepare the final for that version now:** render it from his `approved_src`, upload it **as a new asset** (a new `/_blob/` id; never re-use an address: «لا تعيد استخدام نفس العنوان»), and write `final: {url, version, made_from: <approved_src>}`. Mark the row handled. One row per film and version. |
| `saved` | the page, after «احفظ الفيلم» | `{film, version, saved_src, final}`: the address of exactly what he saved. No action; mark it handled. |
| `media_fix` | the page (v10), when a film he opens names media that are not studio assets, or more than 20 slides | `{film, version, why: media | too_many, files}`. **Re-upload each file as a new asset** (a new `/_blob/` id) and write the new addresses (and `media_at`) in one write; for `too_many`, cut the carousel to 20. He sees «Claude يرفع الملف من يديد» until then. Mark the row handled. |
| `edit` | the studio editor's «احفظ» | His own text edit of a carousel: `edits [{where, field, before, after}]`, `why?`. Log the lesson in `carousel-edits.md`. The film already waits for his approval. |
| `edit` with `undo: true` | «رجّع النسخة السابقة» | He restored an older text (`from`), and the slides were redrawn. The film waits for his approval. Check the redraw, and log one line. |
| `rule` | «خله قاعدة» on التعلّم | `{key, rule, why, format}`. The page has already added it to `studio/rules`. Write it into the matching reference file by PR the same day, and tell him in one line. |
| `posted` | «تم النشر ✓» | Find the post. The reads fall due at 48 h and 7 days. |
| `flow_edit` | the map's «افحص وطبّق» | See «The workflow map». |
| `flow_lock` | the page, on loading an applied map it refused (unreadable, an error, a locked part touched, or an unknown `base_acts`). Doc id `flow_lock-<applied_at or x>-<content hash>`, written once per refused doc (a changed doc that reuses an old `applied_at` gets its own row): `{version, applied_at, content, pre_lock, diff}`; `version` and `applied_at` only when they are a number and a date | **The page is using the built-in map.** Run `tools/studio/flow-migrate.js` on the doc and show him the dropped edits (the report lists them, removed buttons included). Write the result to `studio/flow` only after his yes. Then mark the row handled. Until then, follow the built-in map («مسار الشغل»). |

## The owner edits a carousel's text himself
The owner, 2 Nov 2026: «some time to edit or change the text on the carousel… shouldn't require a regeneration of the
whole picture». A carousel record with `spec` and `src` shows «✎ عدّل النص بنفسك»: the page draws each slide on the
phone with the kit's own layout (studio-page/index.html, `kitSlide`, a port of tools/carousel/carousel.mjs, the fonts
and the TK overlays published under `carousel-kit/`), with live checks (the cover's 73 characters, 12–32 words, a 2–4
word title, text running into the picture or off the slide, words outside the carousel's language, the reader's
question on the last slide). Saving uploads only the changed slides as assets (`/_blob/<id>` in `slides`), writes the
new `spec`, caption and version, keeps the old one in `history`, and leaves a note in `inbox`.
Each save also keeps **what the owner changed, word for word**: `changes[0].edits` (`[{where, field, key, before,
after}]`, the change log shows the changed words «before» ← «after») and the owner's optional «ليش غيّرته؟» (`why`),
copied into the inbox note. Log every one in `references/carousel-edits.md` with its lesson
(`tools/carousel/edits.py <record.json>` prints the entry) before the next carousel is written.
So when Claude next changes that carousel, **the record's `spec` is the truth**: write it to the working folder's
spec.json before rendering. A new carousel gets `spec` and `src` when it is first delivered (its folder published under
`src/carousel/<id>/`). Keep `carousel.mjs` and `kitSlide` in step: a layout change goes into both.

`studio/recipe` `{updated, items: [{rule, why, from}]}`: the algorithm recipe, shown on the films list; Claude writes it from
analysed numbers only (`references/insights.md`).

## One copy only (the owner, 3 Nov 2026: «امسح القديم دايما خل يكون بس في نسخه وحده من اخر تحديث»)
The studio holds **one copy of each film or carousel: its latest version**. The one exception: while a version waits for the owner, the light copy of the version before it stays as `prev_video` for the side-by-side compare, and goes with his approval. Every publish of a new version removes
the files of the one before it in the same call (`files: {"film/<id>-vN.mp4": null, …}`), and the uploaded slides
(`/_blob/…` assets) that only an older version used are deleted. A film keeps one video: once the 1080 final exists,
`video` points to it too and the light copy is removed. The record keeps its `changes` log (text) and `versions`
list, but no `history` of old slides. Local copies and the originals stay outside the studio (never deleted). The
studio's size limit (256 MB a version) is reached quickly otherwise: on 3 Nov 2026 a publish was refused at 254 files.

## The studio's rule texts follow the repo
`library.json` (`direction`, `workflow`, `methods`) and `studio/rules` repeat rules that live in `storytelling.md`,
`ai-film.md`, `hooks.md` and `kuwaiti-voice.md`. When one of those rules is merged, update the studio's copy in the
same change (7 Nov 2026 audit, gap G8: the studio still showed 35–45 shots a minute and music 5 dB under the voice
after the owner had set 22–28 shots and about 20 dB under in the gaps). A rule the owner accepts from the numbers
(«أضيفها للقواعد؟») is written into the matching reference file the next time Claude works, not only into
`studio/rules`. The free review voice may be sped up for listening (`atempo`); the final voice never is.

The forecast on the publish view is the account's usual for that kind until the model uses the film's own features;
it is labelled «المعتاد لريلزكم», never «التوقع» (G9).

## «مسار الشغل»: the workflow map is the studio's control panel
The owner, 7 Nov 2026: «I want the Interactive Visual Workflow Builder to become the central place for designing,
understanding, and controlling the entire Studio workflow… changes should affect how the Studio actually operates».
The studio's `#flow` view draws the whole workflow: three lanes (أنت / Claude / الاستديو) and the 7 stages plus
«طول الوقت». Every step, decision, paid gate and feedback loop has its rules, with their sources, and its settings.
The map was built from evidence only: the page, `library.json`, this skill and its references. Its built-in copy is
`studio-page/flow-seed.json`; the applied map lives in `studio/flow` `{version, applied_at, nodes, edges, history}`.
Known gaps stay on the map, flagged `gap:true`, until they are fixed.

- **The hard rules are locked on the map** (the owner, 7 Nov 2026: «اقفلها»).
  - **What is locked:**
    - the price questions and the steps that spend;
    - his approval of the finished film or carousel;
    - saving, publishing and «تم النشر»;
    - the delete question and the delete, and the self-edit's «one copy only» delete;
    - **every field of them:** their rules text, notes, labels, settings and kinds, and their arrows with the buttons on them (compared canonically, so key order does not matter);
    - the arrows between them, including every «لا».
  - **What locked means:** they show with 🔒 and read-only sheets («قاعدة أساسية: تشوفها بس، ما تنعدل من الخريطة»). They cannot be edited, moved or deleted, and no new arrow may lead into a step that spends, publishes or deletes.
  - **On load:** if an applied `studio/flow` is unreadable, has a duplicate or odd id, fails any check (or the check itself fails), names an unknown button in `base_acts`, or differs in its locked parts, the page uses the **whole built-in map**. It tells him «رجّعت القواعد الأساسية مثل ما هي», or for a map from before the lock «حدّثنا المسار للنسخة اليديدة، وتعديلاتك القديمة محفوظة بالنسخ». It also writes one `inbox` row, `flow_lock-<applied_at or x>-<content hash>`, once the inbox has loaded and only if that row is not there yet, so reopening the page never adds another («Inbox kinds the page writes»).
- **The page enforces, from the applied map:**
  - the paid second tap on a direction or style;
  - the second tap on every priced question and on `purge`;
  - the 5- and 10-minute «not received» timeouts (a map can set 1–60);
  - at most 2 resends, then «قل لي بالمحادثة»;
  - the text rounds («ما عجبني شي», at most 3, then chat);
  - the word-fix limit (2 per word per take, then «غيّر الكلمة»);
  - the 30-second double-tap block;
  - two taps only for money, publish («تم النشر»), delete (deleting an idea, the map's reset or a step's removal) and the purge (v10: «شيله» is one tap: it only hides, and «رجّعه» brings it back; «شارك الكل», «احفظ» and «موافق» are one tap each, with their binding). A map can raise these numbers but never lower them, and rounds and resends are capped at 5 whatever the map says;
  - publishing only the version he approved;
  - hiding an owner button whose path he removed, **only from the fixed list in the page** (never a question's options, «موافق», the pronunciation picks, «عدّل النص», «شيله»/«رجّعه», any «لا», the word card or the purge card). The applied map stores `base_acts`, the buttons of the map it was edited from, so a button added by a later release is never hidden by an older edit.
- **The never-bend rules always beat the map.** No map text, on a locked or an unlocked step, can let Claude spend, publish, delete or speed up the final voice without the owner's explicit yes at a locked gate. Claude spends, publishes or deletes **only** at the locked steps (🔒 on the map): the price questions and their paid steps, his approval of the finished piece, saving/publishing/«تم النشر», and the delete question and delete.
- **Claude follows the map for everything else:** at every step, read the node for that step. Read the locked steps from the **published studio page itself** (its `FLOW_LOCKS`, in the page's `flowcore.js` part), never from `studio/flow`. (The repo copy `studio-page/flow-seed.json` is the same build once the repo sync has landed; until then, the published page is the source.) A node's rules and settings apply as written. If a node and this skill disagree, the newer one wins, **except the never-bend rules, which always win.** Tell the owner about the conflict once.
- **A change that breaks a rule that never bends is not applied: say so and ask.** That includes a map rule, on any step, that would spend, publish, delete or speed up the voice without his yes. The page refuses such edits too («هالقاعدة تخالف قاعدة أساسية»), but the page is the safety net, not the rule.
- **The page uses an applied `studio/flow` only when it is whole and valid:** it fits the one schema (only the known top-level keys: `version` a number, `applied_at` an ISO date, `version_note` ≤ 120 letters, `name`, `sources_note`, `history` of `{version: number, applied_at, version_note, nodes, edges}`, `base_acts` ≤ 100 of this build's buttons, `nodes` ≤ 400, `edges` ≤ 600, the doc ≤ 400 KB without its history; every arrow `kind` is `next`, `yes`, `no` or `loop`; every step is in a band of the doc; the lane names are the fixed ones), has no duplicate or odd ids, passes every check, and leaves the locked parts exactly as built (canonically compared). Otherwise it uses the whole built-in map and keeps **nothing** from the refused doc but a checked numeric version, and writes one `flow_lock` row for that doc («Inbox kinds the page writes»). In both cases the locked steps come from the build.
- **While ANY `flow_lock` row is unhandled, follow the built-in map**, not `studio/flow`, until every such row is handled («Inbox kinds the page writes»). That is what the page shows him too. (A row's `applied_at` can be empty, and its `content` hash is the page's own; never try to match them yourself.)
- **Act only on what he saw.** Every row a tap writes carries what the button was drawn with: `seen_version`, `seen_src` (the video or slides on his screen, **never the final**: v8), for a question `q`, `options` and `price`, for «أعد الإرسال» `seen_text`, for the purge card `seen_asked_at` and `seen_list`, and for the word and hook/title cards `seen_version`. **Act on a row only when they still match the record** (the same `version`, the same file, the same question and price). If anything differs, do nothing with it: ask him again in the studio («وصلت نسخة يديدة / تغيّر السعر، تأكد»), and mark the row handled with why. The page already refuses a tap on a screen that changed under it («تغيّر الفلم من شفته: هذي النسخة اليديدة»), shows «فيه نسخة يديدة، اضغط للتحديث» while he is watching or typing, refuses for about a second any button whose content changed on a redraw («تغيّرت: شيّك قبل لا تضغط»), and counts the second tap of a two-tap confirmation only 600 ms after the first and from a new press, but rows written by the old page, or in chat, have no `seen_*`: for those, `version` on an approve row must equal the record's `version`.
- **The map can never hide a safety control.** Whatever `studio/flow` says, the page always shows: a question's options (every «لا», «مو الحين», «خلّها» included), «موافق», the pronunciation picks, «عدّل النص», «شيله»/«رجّعه», «ما عجبني شي», the change notes, the word card and the purge card. A map can hide only the buttons on a fixed list in the page (`FLOW_HIDEABLE`), and only when he removed their arrow.
- **The page's text check is a safety net, not the rule (شبكة أمان، القاعدة الأساسية تفوز دايماً).** It reads every string **and every key** of each unlocked step, arrow, band and lane, and the doc's `name`, `version_note`, `sources_note` and the history notes, except the fixed-form values of `id`, `from`, `to`, `kinds`, `kind`, `lane`, `type`, `band`, `act`/`acts`, `ask_key`, `row`, `gap_id`, `stage` and the true/false flags (anything else in those is read as text too). It folds the text first (NFKC, so presentation forms and fullwidth letters become plain; invisible format characters and diacritics removed; أإآ→ا, ى→ي, ة→ه) and refuses: the known words for spending, publishing, deleting, speeding up, sharing, approving and buying (Arabic and English), markup (`<…>`), and direction overrides, in any text that is not the built-in wording of that very step and field. It can miss a new phrasing. Whatever it misses, the never-bend rules above still win.
- **Applying an edit:** «افحص وطبّق» refuses:
  - any change to the locked rules, including their rule text and the buttons on their arrows;
  - a new or unlocked step that spends, publishes, deletes or approves (those happen only at locked steps), and a copy of a locked step;
  - the known words for spending, publishing, deleting, speeding up, sharing, approving and buying, markup and direction overrides, in any text or key that is not the built-in wording of that very step and field (exactly what is read is in «مسار الشغل», above). **It is a net, not a proof:** it can miss a new phrasing, and the never-bend rules win whatever it misses (above);
  - «🔒» or «قاعدة أساسية» in any unlocked text (only the locked steps say that);
  - a doc outside the one schema (above): an unknown top-level key, a version that is not a number, a date that is not a date, an arrow kind other than next/yes/no/loop, or one over the size caps;
  - a new step or arrow right after a locked step that spends (a second spend under one yes);
  - a `base_acts` that names anything but this build's buttons; an id outside `a–z`, `0–9`, `_`; an unreadable doc;
  - a timeout outside 1–60 minutes;
  - a gate arrow other than «إي» or «لا»; a duplicate arrow;
  - spend without a «إي» on that very price (one price, one spend);
  - a gate or confirmation with no «لا»;
  - publishing approval on anything but the finished film or carousel;
  - a voice faster than 1 (the free review voice keeps its own speed);
  - spending outside Claude's lane;
  - an arrow that shows on no map;
  - a one-tap confirmation;
  - rounds or resends outside 1–5;
  - a dead end or an unreachable step.

  Removing an unlocked «يعتمد على Claude» note or a gap is a warning he must tick. It cannot check that Claude actually asks: those steps are badged «يعتمد على Claude». Known gaps are drawn as «ثغرة» until they are fixed.

  **A change that breaks a rule that never bends («never publish without his approval», «no paid generation without his yes») is not applied: say so and ask** (above).

  An applied edit adds `{kind: 'flow_edit', text, diff}`. Claude writes the change into the matching reference file or SKILL.md through a PR (merged when the tests pass), marks the row handled, and tells him in one line what now works differently.

## Ideas: captured from the first tap (the owner, 7 Nov 2026)
Every idea lives in the studio from the moment it is sent, whatever the door:
- **«فكرة جديدة»** (home, or the top of المكتبة): the owner types the topic, the type (or «Claude يختار») and the
  language, with an optional link or photo. The page writes `films/<id>` named after the topic, with
  `idea {text, type, lang, link, image}` and `flow.stage: 'queued'`. When the type is `auto`, propose reel or
  carousel with a one-line reason as an `asks` question; never start before he picks.
- **«ريل عجبك»**: a video (up to 20 MiB, uploaded to the page) or a link, plus «شنو عجبك فيه؟»:
  `idea {kind: 'recreate', video, link, note}`. Instagram links cannot be downloaded from the cloud; when only a
  link arrives, ask him once for the saved video in chat.
- **An idea sent in chat**: write its `films` record within minutes (`idea.via: 'chat'`, his words), and an inbox row
  with `handled_at`, so the studio shows «Claude استلم ✓». A chat idea that is not started now goes to `ideas`.
- **«أفكار تنتظر»**: the `ideas` collection `{text, type?, lang?, link?, image?, source: owner|claude|brief, at,
  order, status: waiting|started|dropped, film?}`. Ideas from the daily brief or from research go here as
  `source: claude` or `brief`, never straight into a film. «ابدأ» starts one; «احذف» marks it dropped.
- **Before research**, check that the topic was not already made: the page shows «يشبه…» while he types, as a hint
  only. Claude also searches `films`, `studio/topics` and `ideas`, and tells him in one line if it overlaps.
- **«ما عجبني شي»** on the directions: he writes what he wants instead (`flow.more {text, round}`). Make 3 new free
  directions each round. After 3 rounds, continue in chat.
- A style marked «يحتاج بناء» shows its build time and cost only when `library.json` gives them; otherwise say both
  before starting, as for any paid step.
- «ابدأ بهالنوع» in المكتبة opens «فكرة جديدة» with the type and the format already chosen, «الاثنين» included.
- With «Claude يختار», the record starts as `kind: 'reel'` until you propose and he picks (`asks` key `format`). If he picks «الاثنين», create the carousel record yourself, with `of` and its own request row.
- Every retry loop has a limit:
  - sample «تعديل»: 3, then chat;
  - full retakes of the voice: 3, then chat (change the script or the voice).

## The script card (the owner, 7 Nov 2026)
With every script sent for approval, write on the film:
- `script {version, lines: [{n, text, src: [{title, url?}]}], hook: {chosen, options: [2]}, title: {chosen, options: [2]},
  est_seconds, est_chars, readers: [{who, round, found, fixed}]}`. The page reads the script from here first. The
  «السكربت:» lines in `changes` stay as the fallback. `est_chars` is counted the way ElevenLabs bills (emotion tags
  included). He picks the hook and the title on the card (`inbox` kind `answer`, key `hook` / `title`).
- `words_check {at, items: [{line, word, kind: ask|new, say?, note?, options?}]}` from `director/kw.check`, before the
  voice cost question. His answer arrives as `inbox` kind `words` `{cleared, fixes: [{word, how}]}`. Add the fixes to
  `brand/kuwaiti-words.json` the same day, and list the cleared words under the film's `kw_ok:`.
- A free review voice (`script_audio`, edge-tts) with **every** new script, for every film.
- After each paid whole take, `voice.takes` +1. Set `voice.learned` to the number of words in the word book.
- His edit to a script starts one readers' round on the changed lines only. It does not count toward the 3 rounds.
  Log the edit in `script-edits.md`.

## Every «no» has a written path (the owner, 7 Nov 2026: «طبق كل توصياتك»)
- **Voice cost refused** («مو الحين» / «لا»): nothing is recorded. The film waits at the voice step («التسجيل موقّف
  لين تقول»), and he can edit the script or say «رجّع اسألني بعدين». Do not ask again on your own; ask once more only
  when the script changes.
- **Every paid take asks first, re-takes included.** A take that sounds patched, or a word fix, is a new paid take: the
  same price question, with the billed characters, before any call: key `voice_cost:full` for a whole take,
  `voice_cost:opt` for three spoken options, `voice_cost:lines` for re-recorded lines. Splicing to try a fix is
  free only when it reuses audio already paid for.
- **No style fits**: «شنو تبي بداله؟» on the style card (`flow.more {text, round, of: 'style'}`), 3 new free options a
  round, at most 3 rounds, then chat.
- **Paid AI sample edits**: changing or regenerating an AI sample is a new paid call. Ask first, with the credit
  estimate (`asks` key `ai_cost:sample` for an idea-stage sample, `ai_cost:style` for a style-stage sample).
- **A missing picture**: write `flow.missing [{id, what, line?}]`. He answers in the studio: «عندي صورة» (his upload),
  «استخدم بديل», or «شيل اللقطة» (`inbox` kind `missing`).
- **Paid generation refused**: use a free alternative (a real photo, a code-drawn scene, a still with a slow move)
  or drop the shot, keep building, and say which in the version's `changes`.
- **«احذفه»**: the page hides the film itself (`hidden`, `hidden_at`) and offers «رجّعه». Nothing is deleted without his yes; the hidden list says «ينعرض عليك للمسح بعد N يوم».
- **Once a week, by id** (prompt: `tools/studio/weekly-task.md`; tool: `tools/studio/purge-plan.py`):
  - The weekly task writes `studio/purge` `{asked_at, status: 'open', films: [{id, name, kind, version}]}`, leaving out any film he kept in the last 30 days.
  - The studio shows it on the home page: only the films that are still hidden, each with the name, kind and version **from its own record**. **Every box starts empty.** He ticks which go, and «امسح المختارة» takes two taps.
  - His answer is the inbox row `{kind: 'answer', key: 'purge', answer, ids, asked, asked_at}`. A yes in chat counts only once it is written as that row, with `via: 'chat'` and the ids. A yes with no `ids` is not an answer.
- **What gets deleted:** only ids in that row which are in the question, still hidden, and hidden at least 30 days before `asked_at` (a question or a row with no `asked_at` string matches nothing). Delete each record and **exactly the files `purge-plan.py delete` lists for it, one by one, by their exact path** (its blobs, and the published paths its own `video`, `final`, `slides`, `prev_video`, `poster`, `voice` and `posted` name), **except a file that anything staying still names**: another film, an idea, or an unhandled inbox row, anywhere in a text or a URL. **Never a pattern, a folder or an id prefix** (v8: `film/rubies-*` matches `rubies-engraving`, and `carousel/halter-1/` holds the posted `halter-1-carousel`). **Re-read each record just before deleting it**, and skip it if it is no longer hidden (`purge-plan.py recheck`). Mark the row handled and close `studio/purge`. Never match by name, and never delete on silence. `tools/studio/purge-plan.py delete` lists exactly this.
- **Styles marked «يحتاج بناء»**: before starting one, tell him the build time and any paid cost, as for any paid step.

## The house rules gate (v9, the owner, 8 Nov 2026; video-director #189)
**The house rules gate** (the owner, 8 Nov 2026: «after writing a text, is there a gateway that will check all those rules… so all those edits will not go to waste»): every owner correction a machine can check lives in `brand/house_rules.yaml`. Run `python3 tools/house_check.py <film.yaml | carousel folder | caption.txt> --fix` after writing any script, slide or caption and before the owner sees it; rewrite what it flags (or, when a flagged word is right in that sentence, list it under the film's `rules_ok:`), and confirm its «remember» lessons. `record_flow.py` refuses a paid take and `make.py` refuses to render while a rule is broken.

- **Before he sees any text,** run `tools/house_check.py` on it (`--fix` rewrites the safe ones: محرك، قالب، بالانس ويل، رجب رجبي، no hashtags or source lines in a caption…), rewrite what it flags, and confirm the `remember` lessons. Three places, as on the map («فحص قواعد البيت»): after the script (before «يرسل لك النص»), after the carousel build and every new carousel version (before its review), and before the film's caption is saved. Then write `house_ok: '<that version>'` (v10).
- **Every «تعديل» of his feeds «يتعلم»:** the same day, a correction a machine can check becomes a rule in `brand/house_rules.yaml` (with `why` = his words and `when`), and a lesson in `carousel-edits.md`. A correction it cannot check goes under `remember`.

**Three checks borrowed from Jakeschincariol/instagram-agent-skill (MIT; the owner, 9 Nov 2026: «borrow ideas. implement 1, 2 and 3 first. Each one becomes a rule in the repo plus an automatic check»):**
- **The feed window.** The feed shows a caption's first 125 characters, then «… more». The first sentence ends inside them and names something concrete (the watch, the brand, a number). `house_check.py` prints that window the way a stranger reads it.
- **Search names in the caption.** We use no hashtags, and Instagram search reads the caption's words: every caption carries the brand and model as people type them, in English letters, with the Arabic name beside it («Rolex Day-Date» and «رولكس دي ديت»). A film's or carousel spec's `search:` list (2–3 phrases) must all appear; `--search` gives it on the command line.
- **The hook and long lines are timed before a paid take.** From our own Faisal takes (12.4 characters a second, pauses included): the first line stays under 3.5 s, and a line over 6 s is split or planned with two shots (`shots:` with 2 or more). `record_flow.py` refuses the take while either is broken. The check catches a long hook; it never chooses between two good hooks: the owner chooses. Where Claude confirms a long hook or line is right for one film, list `hook_time` / `line_time` under its `rules_ok:`.

## v10: light on the phone (the owner's iPhone at 1.5 Mbps; plan-v10)

- **Media are studio assets, every time.** Upload every `video`, `final`, slide and `voice.audio` with the artifact's assets (a new `/_blob/<id>` each upload). Never re-use or overwrite an address, never write a published `film/…`, `carousel/…` or http address into a record. That is what makes the address the bytes: the page then streams the video, fetches each slide once, and shares the copies already on his screen, with no hashing.
- **A «موافق» in chat binds like his tap** (the film record table, `approved_*` row): write the version and the exact addresses he saw, `approved_via: 'chat'`, and the inbox row `{kind: 'approve', via: 'chat', …}`. Do not ask him to tap «موافق» again on the page.
- **Every `media_fix` row is work now:** re-upload as assets, write the new addresses and `media_at` in one write, mark the row handled. (v11: for a posted film, see «v11: re-uploads, posted films and the deploy».)
- **`house_ok` is the version string** you checked («The house rules gate»), never `true`.

## Round 11: how he saves a carousel on his iPhone (the live hotfixes v118–v121 of 8 Nov 2026, kept by this release)

- **His way, confirmed by him on his iPhone:** on the carousel's page he taps «📷 احفظ الكل بالصور» and picks his Shortcut **Save TK Post** from the share sheet; every slide lands in Photos, in order, and the caption is on the clipboard. The page hands over **one zip holding only the slides** (no `caption.txt`), named `<film>-01.jpg`, `-02.png`… by each slide's real type; the Shortcut is *Receive Files from Share Sheet → Extract Archive → Save to Photo Album*. If only «Save file» shows, he saves it and shares it from Files → Downloads to Save TK Post.
- **One slide at a time:** «صورة صورة (اضغط مطوّل)» under it: every slide full width, press and hold → «Save to Photos», from 1. Each image is drawn at its own `/_blob/` address, as live v121 does, never from a `blob:` copy: on 9 Nov 2026 the owner tested on his iPhone that iOS offers no «Save to Photos» on a `blob:` image («مايطلع»). Opening it requests the slides again from their addresses (what that costs depends on the assets' cache header).
- **When he asks how to post a carousel,** say exactly that (the page's «شلون أنشرها من الآيفون؟» has the four steps and the one-time Shortcut setup). Do not send him to Files → Select All → Save Images (the v120 way), and do not ask him to save slides one by one with downloads.
- **What makes it work:** the slides must be studio assets (`/_blob/<id>`, «v10: light on the phone») and his approval must name them (the film record table). Until every slide is on his screen the button says «يجهّز k/N…» and is off; then one tap. Slides at any other address show «Claude يرفع الملف من يديد» and no save at all: re-upload them («v10: light on the phone»).
- **Write slides in a format the phone keeps:** JPEG or PNG (or WebP), with the right content type, so the file names and Photos agree.

## v11: re-uploads, posted films and the deploy (plan-v11)

- **Re-uploading a posted film's file gives the posted bytes at a new address**, so its approval moves with it: in the same write as the new `video` / `slides` / `final`, write `approved_version` = the posted version, `approved_src` (a reel) or `approved_slides` (a carousel) and `approved_file` = the new addresses, `approved_via: 'reupload'`, `approved_at` and `approved_media` = the new `media_at`. Only for the file that was posted; a posted film whose `final` is another version's file (`gleitze`: the v5 file under posted v8) is not re-uploaded until the posted version's own final exists. `tools/studio/reupload.py` writes these ops from a map of old path → new `/_blob/` id.
- **Never write an approval naming an address that is not a studio asset** (`/_blob/<32 hex>`), in any write. Until a posted film's media are assets, the page says «هذا الفلم منشور» there and writes no row.
- **His approval on the record stands.** A record with `approved_version === version` and `approved_slides` / `approved_src` equal to what he sees is approved, whatever `approved_file` holds; do not send it back to waiting.
- **At deploy, re-check the house rules** for every open film and write `house_ok: '<its version>'` (an old `true` shows nothing on the new page).
