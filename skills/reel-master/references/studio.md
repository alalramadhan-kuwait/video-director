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
| `final`, `caption` (a film) | **ready before the owner approves; written at once on approval at the latest** (the owner: «مفروض بعد الموافقه يعطيني الفيديو جاهز للحفظ مع الكابشن»): the film at full size (1080×1920, two-pass to under 16 MB, a published file's limit) and its post caption (hook, the story in two lines, the reader's question, sources, credits, hashtags). An approved film shows «احفظ الفيلم ↗» (the share sheet's Save Video; the caption goes to the clipboard on the same tap) and its caption |
| `acts` | `[{name, time}]` once the voice exists |
| `meta` | type · language · look · voice |
| `done_text` | when done («جاهز للنشر», «منشور») |
| `posted` | `{at, version}`, written by the page's «تم النشر ✓»; the reads fall due 48 h and 7 days after `at` |
| `insights_shots` / `insights_sent` | the owner's uploaded screenshots `[{stage, at, shots}]` / the reads he has sent (`48h`, `7d`) |
| `insights` | Claude's reads `[{stage, at, verdict: good|mid|bad, label, vs, numbers: {name: value}, lessons, next}]` (`references/insights.md`) |
| `kind` | `carousel` for a carousel (a Reel leaves it out) |
| `slides` | a carousel's PNGs in order, as published files (`carousel/<id>/01.png` …) |
| `caption` | the post caption; «شارك الكل» saves one zip of every slide and the caption (the Claude app allows one file per prompt, and its share sheet one file) and copies the caption; the numbers under it save one slide each |
| `of` | the record of the same topic in the other format (a carousel's Reel, a Reel's carousel): the page links the two, or offers «سوّ منه كاروسيل/ريل» |
| `spec`, `src` | a carousel's spec.json (its texts, layouts, pictures) and the published folder of its pictures (`src/carousel/<id>/`): with them the owner edits the text in the studio himself (below) |
| `topic` | **every record** (the owner: «group the topics together, because some are the same topic»): the topic's id (`rubies`, `halter`, `tenten`); the list shows one card per topic, its Reels and carousels as slim rows (kind, version, when it was made in Kuwait time, rules). `studio/topics` names it: `{<id>: {name, color}}`; a new topic gets its entry there |
| `rules` | **with every new version** (the owner: «so I can know the new rules are applied to this or no»): the ids of the newest rules this version follows (the page's `RULES`, or `studio/rules` `{list: [{id, kind: reel|carousel, at, name}]}` when set). Without it a version made after a rule's `at` counts as following it, so write it whenever that would be wrong (a re-render of old work). A new permanent rule goes into `RULES` (and `studio/rules`) with the time it became law, so older versions show «⚠ قبل … قواعد جديدة» |
| `history`, `edited` | the last 10 versions before an edit in the studio (`{version, spec, slides, caption, at}`; «رجّع النسخة السابقة» restores the newest), and `edited: studio` once the owner has changed it there |

The percentage is the share of steps done (step − 1 of 9; 100 when done). `studio/now` holds the line at the top:
`{busy, text, at}` (hidden once it is over 3 hours old and Claude is not busy: keep it current).

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

- **The page enforces what it can from the applied map:** the paid second tap, the 5- and 10-minute «not received»
  timeouts, the 30-second double-tap block, the default «بانتظارك» text, and hiding an owner button whose path was
  removed. Without `studio/flow` it behaves as before.
- **Claude follows the map:** at every step, read `studio/flow` (or the seed) for that step's node. A node's rules
  and settings (paid, max rounds, who decides) apply as written. If a node and this skill disagree, the newer one
  wins. Tell the owner about the conflict once.
- **Applying an edit:** the owner's «افحص وطبّق» runs the checks first: no unreachable step, no dead end, no
  decision with a single exit, no paid step without the owner's yes before it, and no publish without his approval.
  An applied edit adds an `inbox` row `{kind: 'flow_edit', text, diff}`. Claude writes that change into the matching
  reference file or SKILL.md through a PR (merged when the tests pass), marks the row handled, and tells the owner
  in one line what now works differently. A change that breaks a rule that never bends («never publish without his
  approval», «no paid generation without his yes») is not applied: say so and ask.

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
  same voice-cost question (key `voice_cost`), with the billed characters, before any call. Splicing to try a fix is
  free only when it reuses audio already paid for.
- **No style fits**: «شنو تبي بداله؟» on the style card (`flow.more {text, round, of: 'style'}`), 3 new free options a
  round, at most 3 rounds, then chat.
- **Paid AI sample edits**: changing or regenerating an AI sample is a new paid call. Ask first, with the credit
  estimate (`asks` key `ai_cost`).
- **A missing picture**: write `flow.missing [{id, what, line?}]`. He answers in the studio: «عندي صورة» (his upload),
  «استخدم بديل», or «شيل اللقطة» (`inbox` kind `missing`).
- **Paid generation refused**: use a free alternative (a real photo, a code-drawn scene, a still with a slow move)
  or drop the shot, keep building, and say which in the version's `changes`.
- **«احذفه»**: the page hides the film itself (`hidden`, `hidden_at`) and offers «رجّعه». Once a week, list the films
  hidden for over 30 days in chat, and delete them (records and their blobs) only on his yes.
- **Styles marked «يحتاج بناء»**: before starting one, tell him the build time and any paid cost, as for any paid step.
